#!/usr/bin/env python3
"""
CellDIVE OME-TIFF to OME-Zarr Pipeline

Complete workflow for processing microscopy OME-TIFF files:
1. Group image files by region identifier
2. Merge channels into multi-channel OME-Zarr files with pyramids
3. Generate OME-XML companion metadata for QuPath v6.0

Usage:
    python pipeline.py <input_directory> [options]

Examples:
    # Basic usage - process all regions to default output
    python pipeline.py /path/to/images

    # Use QuPath-optimized preset (recommended)
    python pipeline.py /path/to/images --config qupath

    # Use fast preset for quick processing
    python pipeline.py /path/to/images --config fast

    # Specify output directory
    python pipeline.py /path/to/images --output /path/to/output

    # Process specific regions only
    python pipeline.py /path/to/images --regions R000 R001 R002

    # Override preset values with custom parameters
    python pipeline.py /path/to/images --config qupath --workers 16

    # Dry run - see what would be processed without creating files
    python pipeline.py /path/to/images --dry-run
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

# Import grouping functions
from Group_Files import group_ome_tiff_by_region, extract_channel_marker_info

# Import enhanced metadata functions
from ome_metadata_enhanced import create_metadata_for_merged_zarr, assign_channel_color

# Import imaging libraries
try:
    from bioio import BioImage
    from bioio_ome_zarr.writers import Channel, OMEZarrWriter
    BIOIO_AVAILABLE = True
except ImportError:
    BIOIO_AVAILABLE = False
    print("Warning: bioio and bioio_ome_zarr not available")
    print("Install with: pip install bioio bioio-ome-zarr")

try:
    import dask.array as da
    DASK_AVAILABLE = True
except ImportError:
    DASK_AVAILABLE = False

try:
    from zarr.codecs import BloscCodec
    ZARR_AVAILABLE = True
except ImportError:
    ZARR_AVAILABLE = False

# Preconfigured parameters for writing zarr files
PRESET_CONFIGS = {
    'qupath': {
        'workers': 8,
        'compression': 'blosc',
        'compression_level': 3,
        'chunk_size': 512,
        'pyramid_levels': 6
    },
    'fast': {
        'workers': 16,
        'compression': 'lz4',
        'compression_level': 1,
        'chunk_size': 1024,
        'pyramid_levels': 5
    },
    'small': {
        'workers': 4,
        'compression': 'zstd',
        'compression_level': 9,
        'chunk_size': 512,
        'pyramid_levels': 5
    },
    'network': {
        'workers': 4,
        'compression': 'blosc',
        'compression_level': 7,
        'chunk_size': 1024,
        'pyramid_levels': 5
    }
}



def calculate_pyramid_shapes(
    base_shape: tuple,
    num_channels: int,
    num_levels: int = 5,
    downsample_factors: Optional[List[int]] = None
) -> List[tuple]:
    """
    Calculate shapes for each pyramid level.

    Parameters
    ----------
    base_shape : tuple
        Shape of the full resolution image (Y, X)
    num_channels : int
        Number of channels
    num_levels : int, optional
        Number of pyramid levels (default: 5)
    downsample_factors : list of int, optional
        Custom downsample factors (default: [1, 2, 4, 8, 12])

    Returns
    -------
    list of tuple
        List of shapes (C, Y, X) for each pyramid level
    """
    if downsample_factors is None:
        downsample_factors = [1, 2, 4, 8, 12]

    # Ensure we have the right number of factors
    if len(downsample_factors) != num_levels:
        # Generate factors
        downsample_factors = [2**i if i < 4 else 12 for i in range(num_levels)]

    level_shapes = []
    for factor in downsample_factors:
        y_size = int(base_shape[0] / factor)
        x_size = int(base_shape[1] / factor)
        level_shapes.append((num_channels, y_size, x_size))

    return level_shapes


def create_zarr_from_tiff_group(
    tiff_files: List[str],
    channel_names: List[str],
    output_path: Path,
    pyramid_levels: int = 5,
    config: Optional[str] = None,
    chunk_size: Optional[int] = None,
    compression: Optional[str] = "blosc",
    compression_level: int = 5,
    num_workers: Optional[int] = None
) -> bool:
    """
    Create a multi-channel OME-Zarr file from a group of OME-TIFF files.

    Parameters
    ----------
    tiff_files : list of str
        List of OME-TIFF file paths (one per channel)
    channel_names : list of str
        List of channel names for display
    output_path : Path
        Output path for the .zarr file
    config : str
        Pre-configured parameters for writing zarr files (default: None)
    pyramid_levels : int, optional
        Number of pyramid levels to create (default: 5)
    chunk_size : int, optional
        Chunk size for Zarr storage (default: auto-calculated)
    compression : str, optional
        Compression algorithm: 'blosc', 'zstd', 'lz4', or None (default: 'blosc')
    compression_level : int, optional
        Compression level 1-9 (default: 5, balanced speed/size)
    num_workers : int, optional
        Number of parallel workers (default: CPU count)

    Returns
    -------
    bool
        True if successful, False otherwise
    """
    # load in the preconfigured parameters if specified
    if not BIOIO_AVAILABLE:
        print("  Error: bioio package required for Zarr creation")
        return False

    try:
        # Configure Dask if available
        if DASK_AVAILABLE and num_workers is not None:
            import dask
            dask.config.set(scheduler='threads', num_workers=num_workers)
            print(f"  Using {num_workers} parallel workers")
        elif DASK_AVAILABLE:
            import dask
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            dask.config.set(scheduler='threads', num_workers=cpu_count)
            print(f"  Using {cpu_count} parallel workers (auto-detected)")

        print(f"  Loading {len(tiff_files)} images...")

        # Load all images
        images = [BioImage(f) for f in tiff_files]

        # Get image data (YX format) - use Dask arrays if available
        if DASK_AVAILABLE:
            import dask.array as da
            # Load as dask arrays for lazy evaluation
            # get_image_dask_data already returns Dask arrays
            image_data_list = [img.get_image_dask_data('YX') for img in images]
            # Stack into multi-channel array (C, Y, X)
            image_stack = da.stack(image_data_list, axis=0)
        else:
            # Fallback to numpy
            image_data_list = [img.get_image_data('YX') for img in images]
            image_stack = np.stack(image_data_list, axis=0)

        print(f"  Image stack shape: {image_stack.shape}")
        print(f"  Data type: {image_stack.dtype}")

        # Get physical pixel sizes from first image
        first_img = images[0]
        pixel_sizes = first_img.physical_pixel_sizes
        physical_pixel_size = [
            0,  # C dimension has no physical size
            pixel_sizes.Y if pixel_sizes.Y else 1.0,
            pixel_sizes.X if pixel_sizes.X else 1.0
        ]

        print(f"  Physical pixel size: Y={physical_pixel_size[1]}, X={physical_pixel_size[2]} µm")
        
        # Calculate pyramid level shapes
        base_shape = image_stack.shape[1:]  # (Y, X)
        level_shapes = calculate_pyramid_shapes(
            base_shape,
            len(tiff_files),
            num_levels=pyramid_levels
        )

        # Auto-calculate optimal chunk size if not provided
        if chunk_size is None:
            # Heuristic: aim for ~16-64 MB chunks
            target_chunk_bytes = 32 * 1024 * 1024  # 32 MB
            bytes_per_pixel = np.dtype(image_stack.dtype).itemsize
            pixels_per_chunk = target_chunk_bytes // bytes_per_pixel
            # Use square chunks for spatial dimensions
            chunk_size = min(1024, int(np.sqrt(pixels_per_chunk)))
            print(f"  Auto-calculated chunk size: {chunk_size}x{chunk_size} pixels")
        else:
            print(f"  Using custom chunk size: {chunk_size}x{chunk_size} pixels")

        print(f"  Creating {pyramid_levels} pyramid levels:")
        for i, shape in enumerate(level_shapes):
            print(f"    Level {i}: {shape}")

        # Configure compression
        if compression and compression.lower() != 'none':
            print(f"  Using {compression} compression (level {compression_level})")

        # Create Channel objects for bioio with color blind-friendly colors
        # Parse display names from channel_names
        channel_objects = []
        for i, channel_name in enumerate(channel_names):
            parts = channel_name.split('_')
            if len(parts) == 2:
                display_name = parts[1]  # DAPI
            elif len(parts) >= 3:
                display_name = f"{parts[1]}_{('_'.join(parts[2:]))}"  # Cy3_iba1
            else:
                display_name = channel_name

            # Assign color blind-friendly color
            color_hex = assign_channel_color(display_name, i)

            channel_objects.append(
                Channel(label=display_name, color=color_hex)
            )

        # Create OMEZarrWriter
        print(f"  Initializing Zarr writer...")
        writer = OMEZarrWriter(
            store=str(output_path),
            level_shapes=level_shapes,
            dtype=image_stack.dtype,
            zarr_format=2,
            channels=channel_objects,
            axes_names=["c", "y", "x"],
            axes_types=["channel", "space", "space"],
            axes_units=[None, "micrometer", "micrometer"],
            physical_pixel_size=physical_pixel_size
        )

        # Write the data
        print(f"  Writing data to Zarr (this may take a while)...")
        writer.write_full_volume(image_stack)

        print(f"  ✓ Successfully created Zarr file: {output_path}")
        return True

    except Exception as e:
        print(f"  ✗ Error creating Zarr file: {e}")
        import traceback
        traceback.print_exc()
        return False


def process_region(
    region_id: str,
    tiff_files: List[str],
    channel_names: List[str],
    output_dir: Path,
    prefix: Optional[str] = None,
    config: Optional[str] = None,
    pyramid_levels: int = 5,
    magnification: Optional[float] = 20.0,
    chunk_size: Optional[int] = None,
    compression: Optional[str] = "blosc",
    compression_level: int = 5,
    num_workers: Optional[int] = None,
    dry_run: bool = False
) -> bool:
    """
    Process a single region: create Zarr and metadata.

    Parameters
    ----------
    config : str
        Pre-configured parameters for writing zarr files (default: None)
    prefix : str
        Image prefix
    region_id : str
        Region identifier (e.g., "R000")
    tiff_files : list of str
        List of OME-TIFF files for this region
    channel_names : list of str
        List of channel names for this region
    output_dir : Path
        Output directory
    pyramid_levels : int, optional
        Number of pyramid levels (default: 5)
    magnification : float, optional
        Objective magnification (default: 20.0)
    dry_run : bool, optional
        If True, only print what would be done (default: False)

    Returns
    -------
    bool
        True if successful
    """
    print(f"\nProcessing {region_id}...")
    print(f"  Files: {len(tiff_files)}")
    print(f"  Channels: {len(channel_names)}")

    if len(tiff_files) != len(channel_names):
        print(f"  ✗ Error: File count ({len(tiff_files)}) doesn't match channel count ({len(channel_names)})")
        return False

    # Define output path
    if prefix != None:
        zarr_path = output_dir / f"{prefix}_{region_id}.zarr"
    else:
        zarr_path = output_dir / f"{region_id}.zarr"

    if dry_run:
        print(f"  [DRY RUN] Would create: {zarr_path}")
        print(f"  [DRY RUN] Would process channels: {channel_names}")
        return True

    # Step 1: Create OME-Zarr file
    print(f"  Creating OME-Zarr with {pyramid_levels} pyramid levels...")
    zarr_success = create_zarr_from_tiff_group(
        tiff_files,
        channel_names,
        zarr_path,
        pyramid_levels=pyramid_levels,
        chunk_size=chunk_size,
        compression=compression,
        compression_level=compression_level,
        num_workers=num_workers
    )

    if not zarr_success:
        return False

    # Step 2: Create OME metadata for QuPath
    print(f"  Generating OME-XML metadata for QuPath...")
    try:
        metadata_path = create_metadata_for_merged_zarr(
            zarr_path=zarr_path,
            tiff_files=tiff_files,
            channel_names=channel_names,
            image_name=f"Region_{region_id}",
            magnification=magnification
        )
        print(f"  ✓ Metadata written to: {metadata_path}")
    except Exception as e:
        print(f"  ✗ Error creating metadata: {e}")
        import traceback
        traceback.print_exc()
        return False

    print(f"  ✓ Successfully processed {region_id}")
    return True


def main():
    """Main pipeline entry point."""
    parser = argparse.ArgumentParser(
        description="CellDIVE OME-TIFF to OME-Zarr Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all regions with default settings
  python pipeline.py /path/to/images

  # Use QuPath-optimized preset (recommended)
  python pipeline.py /path/to/images --config qupath

  # Use fast preset for maximum speed
  python pipeline.py /path/to/images --config fast

  # Use small preset for minimum file size
  python pipeline.py /path/to/images --config small

  # Process specific regions
  python pipeline.py /path/to/images --regions R000 R001

  # Override preset with custom workers
  python pipeline.py /path/to/images --config qupath --workers 16

  # Dry run
  python pipeline.py /path/to/images --dry-run
        """
    )

    parser.add_argument(
        'input_directory',
        type=str,
        help='Directory containing OME-TIFF files'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output directory for Zarr files (default: input_directory/zarr_output)'
    )

    parser.add_argument(
        '--prefix', '-p',
        type=str,
        default=None,
        help='Prefix to add to output file names. If none provided, output files only include region IDs (e.g., R000.zarr).'
    )    

    parser.add_argument(
        '--regions', '-r',
        nargs='+',
        default=None,
        help='Specific region IDs to process (e.g., R000 R001). If not specified, processes all regions.'
    )

    parser.add_argument(
        '--config',
        type=str,
        default=None,
        choices=['qupath', 'fast', 'small', 'network'],
        help='''Pre-configured settings optimized for different use cases:
              qupath (recommended): Balanced for QuPath viewing (8 workers, blosc-3, 512 chunks, 6 pyramids)
              fast: Maximum speed (16 workers, lz4-1, 1024 chunks)
              small: Minimum file size (4 workers, zstd-9, 512 chunks)
              network: Optimized for network/cloud storage (4 workers, blosc-7, 1024 chunks)
              Individual parameters can still override preset values.'''
    )

    parser.add_argument(
        '--pyramid-levels', '-pl',
        type=int,
        default=5,
        help='Number of pyramid levels to create (default: 5)'
    )

    parser.add_argument(
        '--magnification', '-m',
        type=float,
        default=20.0,
        help='Objective magnification (default: 20.0X). Set to 0 to omit magnification metadata.'
    )

    # Performance options
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=None,
        help='Zarr chunk size in pixels (default: auto-calculated for ~32MB chunks)'
    )

    parser.add_argument(
        '--compression',
        type=str,
        default='blosc',
        choices=['blosc', 'zstd', 'lz4', 'none'],
        help='Compression algorithm (default: blosc). Use "none" to disable compression. All lossless compression algorithms.'
    )


    parser.add_argument(
        '--compression-level',
        type=int,
        default=5,
        choices=range(1, 10),
        metavar='1-9',
        help='Compression level 1-9 (default: 5). Higher = better compression, slower.'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers (default: auto-detect CPU count)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without creating files'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Apply preset configuration if specified
    if args.config:
        preset = PRESET_CONFIGS[args.config]
        print(f"Applying '{args.config}' preset configuration...")
        print()

        # Only override arguments that weren't explicitly set by user
        # Check each argument by comparing to its default value
        if args.workers is None:
            args.workers = preset['workers']
        if args.compression == 'blosc':  # Default value
            args.compression = preset['compression']
        if args.compression_level == 5:  # Default value
            args.compression_level = preset['compression_level']
        if args.chunk_size is None:
            args.chunk_size = preset['chunk_size']
        if args.pyramid_levels == 5:  # Default value
            args.pyramid_levels = preset['pyramid_levels']

    # Validate input directory
    input_dir = Path(args.input_directory)
    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        sys.exit(1)

    if not input_dir.is_dir():
        print(f"Error: Input path is not a directory: {input_dir}")
        sys.exit(1)

    # Set output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = input_dir / "zarr_output"

    # Create output directory
    if not args.dry_run:
        output_dir.mkdir(exist_ok=True, parents=True)
    # Handle prefix parameter
    prefix = args.prefix if args.prefix != None else None
    # Handle magnification parameter
    magnification = args.magnification if args.magnification > 0 else None

    # Handle compression parameter
    compression = args.compression if args.compression.lower() != 'none' else None

    print("=" * 70)
    print("CellDIVE OME-TIFF to OME-Zarr Pipeline")
    print("=" * 70)
    print()
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
    if prefix is not None:
        print(f"Prefix:    {prefix}")
    else:
        print(f"Prefix:    No file naming prefix provided, default to only region IDs")
    print(f"Pyramid levels:   {args.pyramid_levels}")
    if magnification is not None:
        print(f"Magnification:    {magnification}X (default: 20.0X)")
    else:
        print(f"Magnification:    Not included in metadata")

    # Performance settings
    print()
    if args.config:
        print(f"Performance Settings (using '{args.config}' preset):")
    else:
        print("Performance Settings:")
    if args.chunk_size:
        print(f"  Chunk size:     {args.chunk_size}x{args.chunk_size} pixels (custom)")
    else:
        print(f"  Chunk size:     Auto-calculated (~32MB chunks)")

    if compression:
        print(f"  Compression:    {compression} (level {args.compression_level})")
    else:
        print(f"  Compression:    Disabled")

    if args.workers:
        print(f"  Workers:        {args.workers} (custom)")
    else:
        import multiprocessing
        print(f"  Workers:        {multiprocessing.cpu_count()} (auto-detected)")

    if args.dry_run:
        print()
        print("Mode:             DRY RUN (no files will be created)")
    print()

    # Check dependencies
    if not args.dry_run:
        if not BIOIO_AVAILABLE:
            print("Error: Required packages not available")
            print("Install with: pip install bioio bioio-ome-zarr bioio-ome-tiff")
            sys.exit(1)

    # Step 1: Group files by region
    print("Step 1: Grouping files by region")
    print("-" * 70)

    try:
        file_groups = group_ome_tiff_by_region(input_dir)
    except Exception as e:
        print(f"Error grouping files: {e}")
        sys.exit(1)

    if not file_groups:
        print("Error: No OME-TIFF files found matching the naming convention")
        print("Expected format: *_R###_*_FINAL*.ome.tif")
        sys.exit(1)

    print(f"Found {len(file_groups)} regions:")
    for region_id, files in file_groups.items():
        print(f"  {region_id}: {len(files)} files")
    print()

    # Step 2: Extract channel information
    print("Step 2: Extracting channel information")
    print("-" * 70)

    try:
        channel_info = extract_channel_marker_info(input_dir)
    except Exception as e:
        print(f"Error extracting channel info: {e}")
        sys.exit(1)

    print(f"Extracted channel info for {len(channel_info)} regions")
    if args.verbose:
        for region_id, channels in channel_info.items():
            print(f"  {region_id}: {channels}")
    print()

    # Filter regions if specified
    if args.regions:
        regions_to_process = [r for r in args.regions if r in file_groups]
        if not regions_to_process:
            print(f"Error: None of the specified regions found: {args.regions}")
            print(f"Available regions: {list(file_groups.keys())}")
            sys.exit(1)
        print(f"Processing {len(regions_to_process)} specified regions: {regions_to_process}")
    else:
        regions_to_process = list(file_groups.keys())
        print(f"Processing all {len(regions_to_process)} regions")

    print()

    # Step 3: Process each region
    print("Step 3: Creating OME-Zarr files with metadata")
    print("-" * 70)

    success_count = 0
    failed_regions = []

    for region_id in regions_to_process:
        success = process_region(
            region_id=region_id,
            tiff_files=file_groups[region_id],
            channel_names=channel_info[region_id],
            output_dir=output_dir,
            prefix=args.prefix,
            config=args.config,
            pyramid_levels=args.pyramid_levels,
            magnification=magnification,
            chunk_size=args.chunk_size,
            compression=compression,
            compression_level=args.compression_level,
            num_workers=args.workers,
            dry_run=args.dry_run
        )

        if success:
            success_count += 1
        else:
            failed_regions.append(region_id)

    # Summary
    print()
    print("=" * 70)
    print("Pipeline Complete")
    print("=" * 70)
    print()
    print(f"Successfully processed: {success_count}/{len(regions_to_process)} regions")

    if failed_regions:
        print(f"Failed regions: {', '.join(failed_regions)}")
        sys.exit(1)
    else:
        if not args.dry_run:
            print()
            print(f"Output files created in: {output_dir}")
            print("Files are ready to open in QuPath v6.0")
            print()
            print("Next steps:")
            print("  1. Open QuPath v6.0")
            print("  2. Drag and drop the .zarr folders into QuPath")
            print("  3. QuPath will read the OME/METADATA.ome.xml for channel information")
        sys.exit(0)


if __name__ == "__main__":
    main()
