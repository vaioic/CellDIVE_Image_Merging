"""
Complete Workflow Example: OME-Zarr Creation with Metadata

This example demonstrates the complete workflow:
1. Group image files by region
2. Extract channel/marker information
3. Create OME-Zarr files (your existing workflow)
4. Generate companion OME metadata for QuPath
"""

from pathlib import Path
from group_ome_tiff_files import group_ome_tiff_by_region, extract_channel_marker_info
from ome_zarr_metadata import create_ome_metadata_for_zarr

# Check if required packages are available
try:
    import ome_types
    OME_TYPES_AVAILABLE = True
except ImportError:
    OME_TYPES_AVAILABLE = False


def complete_workflow_example(
    image_directory: str,
    output_directory: str,
    template_tiff_path: str = None
):
    """
    Complete workflow from raw TIFF files to OME-Zarr with metadata.
    
    Parameters
    ----------
    image_directory : str
        Directory containing the raw OME-TIFF files
    output_directory : str
        Directory where Zarr files will be created
    template_tiff_path : str, optional
        Path to a template TIFF with microscope metadata
    """
    
    print("="*70)
    print("OME-ZARR WORKFLOW WITH METADATA GENERATION")
    print("="*70)
    print()
    
    # Step 1: Group files by region
    print("Step 1: Grouping files by region")
    print("-"*70)
    
    file_groups = group_ome_tiff_by_region(image_directory)
    
    if not file_groups:
        print("Error: No files found matching the pattern")
        return
    
    print(f"Found {len(file_groups)} regions:")
    for region_id, files in file_groups.items():
        print(f"  {region_id}: {len(files)} files")
    
    print()
    
    # Step 2: Extract channel/marker information
    print("Step 2: Extracting channel and marker information")
    print("-"*70)
    
    channel_info = extract_channel_marker_info(image_directory)
    
    print(f"Extracted channel info for {len(channel_info)} regions:")
    for region_id, channels in channel_info.items():
        print(f"  {region_id}: {channels}")
    
    print()
    
    # Step 3: Process each region
    print("Step 3: Processing each region")
    print("-"*70)
    
    output_dir = Path(output_directory)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    for region_id in file_groups.keys():
        print(f"\nProcessing {region_id}...")
        
        # Get files and channel info for this region
        region_files = file_groups[region_id]
        region_channels = channel_info[region_id]
        
        # Define output Zarr path
        zarr_path = output_dir / f"{region_id}.zarr"
        
        print(f"  Input files: {len(region_files)}")
        print(f"  Channels: {len(region_channels)}")
        print(f"  Output: {zarr_path}")
        
        # Step 3a: Create OME-Zarr (YOUR EXISTING WORKFLOW GOES HERE)
        print(f"  → Creating OME-Zarr file...")
        # YOUR CODE HERE - Example:
        # create_ome_zarr(region_files, zarr_path, ...)
        
        # For demonstration, create a dummy zarr directory
        zarr_path.mkdir(exist_ok=True, parents=True)
        
        # Step 3b: Generate companion OME metadata
        if OME_TYPES_AVAILABLE:
            print(f"  → Generating OME metadata...")
            try:
                metadata_path = create_ome_metadata_for_zarr(
                    zarr_path=zarr_path,
                    channel_info=region_channels,
                    template_tiff_path=template_tiff_path,
                    image_name=f"Region_{region_id}",
                    size_x=2048,  # Adjust to your image size
                    size_y=2048,  # Adjust to your image size
                    size_z=1,     # Adjust if you have Z-stacks
                    size_t=1,     # Adjust if you have time series
                    pixel_type="uint16"  # Adjust to your data type
                )
                print(f"  ✓ Metadata written to: {metadata_path}")
            except Exception as e:
                print(f"  ✗ Error generating metadata: {e}")
        else:
            print(f"  ⚠ Skipping metadata (ome-types not installed)")
        
        print(f"  ✓ Completed {region_id}")
    
    print()
    print("="*70)
    print("WORKFLOW COMPLETE")
    print("="*70)
    print()
    print(f"Output directory: {output_directory}")
    print(f"Created {len(file_groups)} OME-Zarr files")
    if OME_TYPES_AVAILABLE:
        print("✓ Companion OME metadata files created")
        print("  → Files are ready to open in QuPath v6.0")
    else:
        print("⚠ Install ome-types to generate metadata: pip install ome-types")


def minimal_example():
    """
    Minimal example showing just the metadata generation step.
    Use this if you already have Zarr files created.
    """
    print("="*70)
    print("MINIMAL EXAMPLE: Adding Metadata to Existing Zarr")
    print("="*70)
    print()
    
    # Example channel information (you'd get this from extract_channel_marker_info)
    channel_info = [
        '1.0.4_DAPI',
        '1.0.4_Cy3_iba1',
        '1.0.4_Cy5_Neun',
        '1.0.4_FITC_GFAP'
    ]
    
    # Path to your existing Zarr file
    zarr_path = "path/to/your/file.zarr"
    
    # Optional: path to template TIFF from your microscope
    template_tiff = None  # or "path/to/template.tif"
    
    print(f"Zarr file: {zarr_path}")
    print(f"Channels: {channel_info}")
    print()
    
    if OME_TYPES_AVAILABLE:
        try:
            # This single function call does everything
            metadata_path = create_ome_metadata_for_zarr(
                zarr_path=zarr_path,
                channel_info=channel_info,
                template_tiff_path=template_tiff,
                size_x=2048,
                size_y=2048
            )
            
            print()
            print(f"✓ Success! Metadata written to: {metadata_path}")
            print()
            print("Your Zarr structure now looks like:")
            print(f"  {zarr_path}/")
            print("    OME/")
            print("      .zgroup")
            print("      METADATA.ome.xml  ← QuPath reads this")
            print("    ... (your existing zarr data)")
            
        except Exception as e:
            print(f"✗ Error: {e}")
    else:
        print("⚠ ome-types package required")
        print("Install with: pip install ome-types")


def troubleshooting_schema_error():
    """
    Example of how to handle the xmlns:schemaLocation error.
    """
    print("="*70)
    print("TROUBLESHOOTING: xmlns:schemaLocation Error")
    print("="*70)
    print()
    
    print("If you get 'xmlns:schemaLocation is not a valid URI' error:")
    print()
    print("Option 1: Use fix_schema=True (default)")
    print("-"*40)
    print("from ome_zarr_metadata import create_ome_from_template")
    print("ome = create_ome_from_template('template.tif', fix_schema=True)")
    print()
    
    print("Option 2: Don't use template, create minimal OME")
    print("-"*40)
    print("Just omit the template_tiff_path parameter:")
    print("create_ome_metadata_for_zarr(zarr_path, channel_info)")
    print()
    
    print("Option 3: Manually fix the template file")
    print("-"*40)
    print("1. Export OME-XML from your microscope software")
    print("2. Open in text editor")
    print("3. Replace 'xmlns:schemaLocation' with 'xsi:schemaLocation'")
    print("4. Save and use as template")


if __name__ == "__main__":
    import sys
    
    print()
    print("OME-ZARR WORKFLOW EXAMPLES")
    print()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "complete":
            # Example: python workflow_example.py complete /path/to/images /path/to/output
            if len(sys.argv) >= 4:
                image_dir = sys.argv[2]
                output_dir = sys.argv[3]
                template = sys.argv[4] if len(sys.argv) > 4 else None
                complete_workflow_example(image_dir, output_dir, template)
            else:
                print("Usage: python workflow_example.py complete <image_dir> <output_dir> [template.tif]")
        
        elif sys.argv[1] == "minimal":
            minimal_example()
        
        elif sys.argv[1] == "troubleshoot":
            troubleshooting_schema_error()
    
    else:
        print("Available examples:")
        print("  python workflow_example.py complete <image_dir> <output_dir>")
        print("  python workflow_example.py minimal")
        print("  python workflow_example.py troubleshoot")
        print()
        print("Or import and use in your own code:")
        print()
        print("  from workflow_example import complete_workflow_example")
        print("  complete_workflow_example('/path/to/images', '/path/to/output')")
