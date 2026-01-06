"""
Enhanced OME Metadata Module for CellDIVE Pipeline

This module creates OME-XML metadata files for OME-Zarr datasets, preserving
imaging parameters from the original OME-TIFF files including:
- Channel names (extracted from filenames)
- Display colors (color blind-friendly palette)
- Exposure times
- Laser power
- Physical pixel sizes
- Magnification
- Other acquisition parameters

Designed for QuPath v6.0 compatibility.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union
import tifffile
from ome_types import from_tiff, from_xml, model
from ome_types.model import OME, Image, Pixels, Channel


# Color blind-friendly palette (high contrast)
# Based on Paul Tol's color schemes and IBM's color blind safe palette
COLORBLIND_FRIENDLY_COLORS = {
    'DAPI': 'FFFFFF',      # White for nuclear stain
    'CY3': 'FFB000',       # Vibrant orange
    'CY5': 'DC267F',       # Magenta/pink
    'CY7': '00FFFF',       # Cyan
    'FITC': '00FF00',      # Bright green
    'default': [
        'FFB000',  # Orange
        'DC267F',  # Magenta
        '00FFFF',  # Cyan
        '00FF00',  # Bright green
        'FE6100',  # Dark orange
        '785EF0',  # Purple
        'FFE119',  # Yellow
        '648FFF',  # Blue
    ]
}


def assign_channel_color(channel_name: str, channel_index: int) -> str:
    """
    Assign a color blind-friendly color to a channel.

    Parameters
    ----------
    channel_name : str
        Channel name (e.g., 'DAPI', 'Cy3_iba1')
    channel_index : int
        Index of the channel (used for fallback colors)

    Returns
    -------
    str
        Hex color code (e.g., 'FFFFFF')
    """
    # Check if DAPI
    if 'DAPI' in channel_name.upper():
        return COLORBLIND_FRIENDLY_COLORS['DAPI']

    # Check for specific fluorophores
    for fluor in ['CY3', 'CY5', 'CY7', 'FITC']:
        if fluor in channel_name.upper():
            return COLORBLIND_FRIENDLY_COLORS[fluor]

    # Fallback to cycling through default colors
    default_colors = COLORBLIND_FRIENDLY_COLORS['default']
    return default_colors[channel_index % len(default_colors)]


def extract_ome_from_tiff_with_fix(
    tiff_path: Union[str, Path]
) -> Optional[OME]:
    """
    Extract OME metadata from a TIFF file with automatic schema fixing.

    Parameters
    ----------
    tiff_path : str or Path
        Path to the OME-TIFF file

    Returns
    -------
    OME or None
        OME object with metadata, or None if extraction fails
    """
    tiff_path = Path(tiff_path)

    if not tiff_path.exists():
        print(f"Warning: TIFF file not found: {tiff_path}")
        return None

    try:
        # Try direct loading first
        ome = from_tiff(tiff_path)
        return ome
    except Exception as e:
        if "schemaLocation" in str(e):
            # Try fixing schema issue
            try:
                with tifffile.TiffFile(tiff_path) as tif:
                    if tif.ome_metadata:
                        xml_string = tif.ome_metadata
                        # Fix schema issues
                        xml_string = xml_string.replace('xmlns:schemaLocation', 'xsi:schemaLocation')
                        if 'xmlns:xsi=' not in xml_string:
                            xml_string = xml_string.replace(
                                '<OME ',
                                '<OME xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                            )
                        ome = from_xml(xml_string)
                        return ome
                    else:
                        print(f"Warning: No OME metadata in {tiff_path.name}")
                        return None
            except Exception as fix_error:
                print(f"Warning: Could not extract metadata from {tiff_path.name}: {fix_error}")
                return None
        else:
            print(f"Warning: Error loading OME from {tiff_path.name}: {e}")
            return None


def merge_ome_metadata_from_files(
    tiff_files: List[Union[str, Path]],
    channel_names: List[str],
    image_name: str = "Merged_Image",
    magnification: Optional[float] = 20.0
) -> OME:
    """
    Create merged OME metadata from multiple TIFF files, preserving imaging parameters.

    This function:
    1. Extracts metadata from the first TIFF (template)
    2. Creates channels for each image with color blind-friendly colors
    3. Preserves physical pixel sizes, exposure times, and other parameters
    4. Updates channel names from filename-derived information
    5. Adds magnification metadata

    Parameters
    ----------
    tiff_files : list of str or Path
        List of OME-TIFF file paths (one per channel)
    channel_names : list of str
        List of channel names (e.g., ['1.0.4_DAPI', '1.0.4_Cy3_iba1'])
    image_name : str, optional
        Name for the merged image
    magnification : float, optional
        Objective magnification (default: 20.0)

    Returns
    -------
    OME
        Merged OME object with all channels and preserved metadata
    """
    if len(tiff_files) != len(channel_names):
        raise ValueError(f"Number of files ({len(tiff_files)}) must match number of channel names ({len(channel_names)})")

    # Extract metadata from first file as template
    template_ome = extract_ome_from_tiff_with_fix(tiff_files[0])

    if template_ome is None or len(template_ome.images) == 0:
        print("Warning: Could not extract template metadata, creating minimal OME")
        # Get image dimensions from first file
        with tifffile.TiffFile(tiff_files[0]) as tif:
            shape = tif.series[0].shape
            if len(shape) >= 2:
                size_y, size_x = shape[-2:]
            else:
                size_y, size_x = 1024, 1024

        # Create minimal OME
        template_image = model.Image(
            id="Image:0",
            name=image_name,
            pixels=model.Pixels(
                id="Pixels:0",
                dimension_order="XYZCT",
                size_x=size_x,
                size_y=size_y,
                size_z=1,
                size_c=len(channel_names),
                size_t=1,
                type="uint16",
                metadata_only=True
            )
        )
        template_ome = OME(images=[template_image])

    # Get template image and pixels
    template_image = template_ome.images[0]
    template_pixels = template_image.pixels

    # Update image name
    template_image.name = image_name

    # Create new channels list
    new_channels = []

    for i, (tiff_file, channel_name) in enumerate(zip(tiff_files, channel_names)):
        # Extract OME from each file to get channel-specific parameters
        file_ome = extract_ome_from_tiff_with_fix(tiff_file)

        # Parse channel name (format: "round_channel_marker" or "round_channel")
        parts = channel_name.split('_')
        if len(parts) == 2:
            # DAPI format: round_channel
            display_name = parts[1]  # "DAPI"
        elif len(parts) >= 3:
            # Marker format: round_channel_marker
            channel = parts[1]
            marker = '_'.join(parts[2:])
            display_name = f"{channel}_{marker}"
        else:
            display_name = channel_name

        # Assign color blind-friendly color
        color_hex = assign_channel_color(display_name, i)

        # Create channel object with color
        channel = Channel(
            id=f"Channel:0:{i}",
            name=display_name,
            samples_per_pixel=1,
            color=color_hex
        )

        # Try to preserve channel-specific parameters from original file
        if file_ome and len(file_ome.images) > 0 and len(file_ome.images[0].pixels.channels) > 0:
            original_channel = file_ome.images[0].pixels.channels[0]

            # Preserve excitation/emission wavelengths (but keep our assigned color)
            if original_channel.excitation_wavelength:
                channel.excitation_wavelength = original_channel.excitation_wavelength
            if original_channel.emission_wavelength:
                channel.emission_wavelength = original_channel.emission_wavelength
            if original_channel.light_source_settings:
                channel.light_source_settings = original_channel.light_source_settings
            if original_channel.detector_settings:
                channel.detector_settings = original_channel.detector_settings

        new_channels.append(channel)

    # Update pixels with new channels
    template_pixels.channels = new_channels
    template_pixels.size_c = len(new_channels)

    # Add magnification metadata if provided
    if magnification is not None:
        # Create or update objective settings
        if not hasattr(template_image, 'objective_settings') or template_image.objective_settings is None:
            # Create minimal objective settings with magnification
            try:
                objective = model.Objective(
                    id="Objective:0",
                    nominal_magnification=magnification
                )
                objective_settings = model.ObjectiveSettings(
                    id="Objective:0"
                )
                template_image.objective_settings = objective_settings

                # Add objective to instrument if it exists
                if template_ome.instruments is None:
                    template_ome.instruments = []
                if len(template_ome.instruments) == 0:
                    instrument = model.Instrument(id="Instrument:0")
                    template_ome.instruments.append(instrument)

                if template_ome.instruments[0].objectives is None:
                    template_ome.instruments[0].objectives = []
                if len(template_ome.instruments[0].objectives) == 0:
                    template_ome.instruments[0].objectives.append(objective)
                else:
                    template_ome.instruments[0].objectives[0].nominal_magnification = magnification

            except Exception as e:
                print(f"  Note: Could not add magnification metadata: {e}")

    return template_ome


def write_ome_xml_to_zarr(
    ome: OME,
    zarr_path: Union[str, Path],
    create_zgroup: bool = True
) -> Path:
    """
    Write OME.XML metadata file to the OME-Zarr structure for QuPath compatibility.

    Creates the companion METADATA.ome.xml file that QuPath needs.

    Parameters
    ----------
    ome : OME
        OME object to write
    zarr_path : str or Path
        Path to the .zarr directory
    create_zgroup : bool, optional
        If True, creates a .zgroup file in the OME directory (default: True)

    Returns
    -------
    Path
        Path to the created METADATA.ome.xml file

    Notes
    -----
    Creates the following structure:
    zarr_path/
        OME/
            .zgroup         (if create_zgroup=True)
            METADATA.ome.xml
    """
    zarr_path = Path(zarr_path)

    if not zarr_path.exists():
        raise ValueError(f"Zarr directory does not exist: {zarr_path}")

    # Create OME subdirectory
    ome_dir = zarr_path / "OME"
    ome_dir.mkdir(exist_ok=True)

    # Create .zgroup file if requested
    if create_zgroup:
        zgroup_path = ome_dir / ".zgroup"
        zgroup_data = {"zarr_format": 2}
        with open(zgroup_path, 'w') as f:
            json.dump(zgroup_data, f)
        print(f"  Created .zgroup at: {zgroup_path}")

    # Write METADATA.ome.xml
    metadata_path = ome_dir / "METADATA.ome.xml"

    # Convert OME to XML string
    xml_string = ome.to_xml()

    # Write to file
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write(xml_string)

    print(f"  Wrote OME metadata to: {metadata_path}")

    return metadata_path


def create_metadata_for_merged_zarr(
    zarr_path: Union[str, Path],
    tiff_files: List[Union[str, Path]],
    channel_names: List[str],
    image_name: Optional[str] = None,
    magnification: Optional[float] = 20.0
) -> Path:
    """
    High-level function to create OME metadata for a merged Zarr file.

    This combines all steps:
    1. Extract and merge metadata from source TIFFs
    2. Update with channel names and color blind-friendly colors
    3. Add magnification metadata
    4. Write to Zarr structure

    Parameters
    ----------
    zarr_path : str or Path
        Path to the .zarr directory
    tiff_files : list of str or Path
        List of source OME-TIFF files (one per channel)
    channel_names : list of str
        List of channel names from extract_channel_marker_info()
    image_name : str, optional
        Name for the image (default: zarr filename)
    magnification : float, optional
        Objective magnification (default: 20.0). Set to None to omit.

    Returns
    -------
    Path
        Path to the created METADATA.ome.xml file

    Examples
    --------
    >>> tiff_files = [
    ...     "R000_DAPI.ome.tif",
    ...     "R000_Cy3_iba1.ome.tif",
    ...     "R000_Cy5_Neun.ome.tif"
    ... ]
    >>> channel_names = ['1.0.4_DAPI', '1.0.4_Cy3_iba1', '1.0.4_Cy5_Neun']
    >>> create_metadata_for_merged_zarr(
    ...     "R000.zarr",
    ...     tiff_files,
    ...     channel_names
    ... )
    """
    zarr_path = Path(zarr_path)

    if image_name is None:
        image_name = zarr_path.stem

    print(f"  Creating OME metadata from {len(tiff_files)} source files...")
    if magnification is not None:
        print(f"  Using magnification: {magnification}X (default: 20.0X)")
    else:
        print(f"  No magnification metadata will be added")

    # Create merged OME with preserved parameters
    ome = merge_ome_metadata_from_files(
        tiff_files,
        channel_names,
        image_name,
        magnification=magnification
    )

    # Write to Zarr structure
    metadata_path = write_ome_xml_to_zarr(ome, zarr_path)

    return metadata_path


# Example usage
if __name__ == "__main__":
    print("Enhanced OME Metadata Module")
    print("=" * 70)
    print()
    print("This module provides functions to create OME metadata for Zarr files")
    print("while preserving imaging parameters from source OME-TIFF files.")
    print()
    print("Key functions:")
    print("  - extract_ome_from_tiff_with_fix(): Extract metadata from TIFF")
    print("  - merge_ome_metadata_from_files(): Merge metadata from multiple TIFFs")
    print("  - create_metadata_for_merged_zarr(): High-level wrapper")
    print()
    print("See pipeline.py for complete workflow integration.")
