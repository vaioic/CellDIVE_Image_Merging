"""
OME-Zarr Metadata Generator

This module provides functions to create OME.XML metadata files for OME-Zarr
datasets, specifically designed for QuPath v6.0 compatibility.

The workflow creates a companion METADATA.ome.xml file in the zarr structure
that QuPath can read, since it cannot read metadata embedded in the zarr itself.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union
from xml.etree import ElementTree as ET

try:
    from ome_types import from_tiff, from_xml, model
    from ome_types.model import OME, Image, Pixels, Channel
    OME_TYPES_AVAILABLE = True
except ImportError:
    OME_TYPES_AVAILABLE = False
    print("Warning: ome-types package not available. Install with: pip install ome-types")


def create_ome_from_template(
    template_tiff_path: Union[str, Path],
    fix_schema: bool = True
) -> Optional[OME]:
    """
    Create an OME object from a template TIFF file with metadata.
    
    This function reads metadata from a TIFF file exported from your microscope
    and creates an OME object that can be modified for the zarr dataset.
    
    Parameters
    ----------
    template_tiff_path : str or Path
        Path to a TIFF file containing microscope metadata
    fix_schema : bool, optional
        If True, attempts to fix common schema location issues (default: True)
    
    Returns
    -------
    OME or None
        OME object with metadata from the template file, or None if import fails
    
    Notes
    -----
    Common issue: "xmlns:schemaLocation is not a valid URI"
    This occurs when the TIFF has malformed schema location attributes.
    The fix_schema parameter attempts to correct this automatically.
    
    Examples
    --------
    >>> ome = create_ome_from_template("microscope_export.tif")
    >>> if ome:
    ...     print(f"Loaded template with {len(ome.images)} images")
    """
    if not OME_TYPES_AVAILABLE:
        print("Error: ome-types package is required")
        return None
    
    template_tiff_path = Path(template_tiff_path)
    
    if not template_tiff_path.exists():
        raise ValueError(f"Template TIFF file not found: {template_tiff_path}")
    
    try:
        # Try direct loading first
        ome = from_tiff(template_tiff_path)
        return ome
        
    except Exception as e:
        if "schemaLocation" in str(e) and fix_schema:
            print(f"Schema location error detected. Attempting to fix...")
            
            # Try reading and fixing the XML manually
            try:
                # Use tifffile to extract OME-XML
                import tifffile
                with tifffile.TiffFile(template_tiff_path) as tif:
                    if tif.ome_metadata:
                        xml_string = tif.ome_metadata
                        
                        # Fix common schema issues
                        xml_string = fix_ome_xml_schema(xml_string)
                        
                        # Parse with ome-types
                        ome = from_xml(xml_string)
                        return ome
                    else:
                        print("No OME metadata found in TIFF file")
                        return None
                        
            except ImportError:
                print("tifffile package required for schema fixing. Install with: pip install tifffile")
                return None
            except Exception as fix_error:
                print(f"Error after attempting fix: {fix_error}")
                return None
        else:
            print(f"Error loading OME from TIFF: {e}")
            return None


def fix_ome_xml_schema(xml_string: str) -> str:
    """
    Fix common schema location issues in OME-XML strings.
    
    Parameters
    ----------
    xml_string : str
        The OME-XML string to fix
    
    Returns
    -------
    str
        Fixed OME-XML string
    """
    # Remove problematic xmlns:schemaLocation if present
    xml_string = xml_string.replace('xmlns:schemaLocation', 'xsi:schemaLocation')
    
    # Ensure proper namespace declarations
    if 'xmlns:xsi=' not in xml_string:
        xml_string = xml_string.replace(
            '<OME ',
            '<OME xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        )
    
    return xml_string


def create_minimal_ome(
    image_name: str = "Image",
    size_x: int = 1024,
    size_y: int = 1024,
    size_c: int = 1,
    size_z: int = 1,
    size_t: int = 1,
    pixel_type: str = "uint16",
    dimension_order: str = "XYZCT"
) -> OME:
    """
    Create a minimal OME object from scratch when no template is available.
    
    Parameters
    ----------
    image_name : str, optional
        Name for the image (default: "Image")
    size_x, size_y : int, optional
        Image dimensions (default: 1024)
    size_c : int, optional
        Number of channels (default: 1)
    size_z : int, optional
        Number of Z slices (default: 1)
    size_t : int, optional
        Number of time points (default: 1)
    pixel_type : str, optional
        Pixel data type (default: "uint16")
    dimension_order : str, optional
        Dimension order (default: "XYZCT")
    
    Returns
    -------
    OME
        Minimal OME object that can be customized
    
    Examples
    --------
    >>> ome = create_minimal_ome(size_x=2048, size_y=2048, size_c=4)
    >>> print(f"Created OME with {ome.images[0].pixels.size_c} channels")
    """
    if not OME_TYPES_AVAILABLE:
        raise ImportError("ome-types package is required")
    
    # Create channel objects
    channels = [Channel(id=f"Channel:0:{i}", name=f"Channel {i}") 
                for i in range(size_c)]
    
    # Create Pixels object
    pixels = Pixels(
        id="Pixels:0",
        dimension_order=dimension_order,
        size_c=size_c,
        size_t=size_t,
        size_x=size_x,
        size_y=size_y,
        size_z=size_z,
        type=pixel_type,
        channels=channels,
        metadata_only=True
    )
    
    # Create Image object
    image = Image(id="Image:0", name=image_name, pixels=pixels)
    
    # Create OME object
    ome = OME(images=[image])
    
    return ome


def update_ome_channels(
    ome: OME,
    channel_info: List[str],
    image_index: int = 0
) -> OME:
    """
    Update OME object with channel information from file naming.
    
    This function takes channel/marker information extracted from filenames
    (e.g., from extract_channel_marker_info) and updates the OME metadata.
    
    Parameters
    ----------
    ome : OME
        OME object to update
    channel_info : list of str
        List of channel info strings in format "round_channel_marker" or "round_channel"
        Example: ['1.0.4_DAPI', '1.0.4_Cy3_iba1', '1.0.4_Cy5_Neun']
    image_index : int, optional
        Index of the image to update (default: 0)
    
    Returns
    -------
    OME
        Updated OME object with channel names
    
    Examples
    --------
    >>> channel_info = ['1.0.4_DAPI', '1.0.4_Cy3_iba1', '1.0.4_Cy5_Neun']
    >>> ome = update_ome_channels(ome, channel_info)
    >>> for i, ch in enumerate(ome.images[0].pixels.channels):
    ...     print(f"Channel {i}: {ch.name}")
    Channel 0: DAPI
    Channel 1: Cy3_iba1
    Channel 2: Cy5_Neun
    """
    if not OME_TYPES_AVAILABLE:
        raise ImportError("ome-types package is required")
    
    if image_index >= len(ome.images):
        raise ValueError(f"Image index {image_index} out of range. OME has {len(ome.images)} images.")
    
    image = ome.images[image_index]
    pixels = image.pixels
    
    # Clear existing channels
    pixels.channels = []
    
    # Add new channels based on channel_info
    for i, info in enumerate(channel_info):
        # Parse the channel info string
        # Format is either "round_channel" (DAPI) or "round_channel_marker"
        parts = info.split('_')
        
        if len(parts) == 2:
            # DAPI format: round_channel
            round_num, channel = parts
            channel_name = channel
        elif len(parts) >= 3:
            # Marker format: round_channel_marker
            round_num = parts[0]
            channel = parts[1]
            marker = '_'.join(parts[2:])  # Handle markers with underscores
            channel_name = f"{channel}_{marker}"
        else:
            # Fallback
            channel_name = info
        
        # Create new channel
        new_channel = Channel(
            id=f"Channel:{image_index}:{i}",
            name=channel_name,
            samples_per_pixel=1
        )
        
        pixels.channels.append(new_channel)
    
    # Update the pixel count
    pixels.size_c = len(pixels.channels)
    
    return ome


def write_ome_xml_to_zarr(
    ome: OME,
    zarr_path: Union[str, Path],
    create_zgroup: bool = True
) -> Path:
    """
    Write OME.XML metadata file to the OME-Zarr structure.
    
    This creates the companion METADATA.ome.xml file that QuPath needs to
    read the metadata correctly.
    
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
    
    The .zgroup file is a Zarr convention to indicate that OME/ is a Zarr group.
    
    Examples
    --------
    >>> xml_path = write_ome_xml_to_zarr(ome, "my_data.zarr")
    >>> print(f"Wrote metadata to: {xml_path}")
    """
    if not OME_TYPES_AVAILABLE:
        raise ImportError("ome-types package is required")
    
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
        print(f"Created .zgroup at: {zgroup_path}")
    
    # Write METADATA.ome.xml
    metadata_path = ome_dir / "METADATA.ome.xml"
    
    # Convert OME to XML string
    xml_string = ome.to_xml()
    
    # Write to file
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write(xml_string)
    
    print(f"Wrote OME metadata to: {metadata_path}")
    
    return metadata_path


def create_ome_metadata_for_zarr(
    zarr_path: Union[str, Path],
    channel_info: List[str],
    template_tiff_path: Optional[Union[str, Path]] = None,
    image_name: Optional[str] = None,
    size_x: int = 1024,
    size_y: int = 1024,
    size_z: int = 1,
    size_t: int = 1,
    pixel_type: str = "uint16"
) -> Path:
    """
    Complete workflow to create OME metadata for a Zarr file.
    
    This is a high-level function that combines all steps:
    1. Create or load OME template
    2. Update with channel information
    3. Write to Zarr structure
    
    Parameters
    ----------
    zarr_path : str or Path
        Path to the .zarr directory
    channel_info : list of str
        List of channel info strings (from extract_channel_marker_info)
    template_tiff_path : str or Path, optional
        Path to template TIFF with microscope metadata. If None, creates minimal OME.
    image_name : str, optional
        Name for the image (only used if creating minimal OME)
    size_x, size_y : int, optional
        Image dimensions (only used if creating minimal OME)
    size_z : int, optional
        Number of Z slices (only used if creating minimal OME)
    size_t : int, optional
        Number of timepoints (only used if creating minimal OME)
    pixel_type : str, optional
        Pixel data type (only used if creating minimal OME)
    
    Returns
    -------
    Path
        Path to the created METADATA.ome.xml file
    
    Examples
    --------
    >>> # With template TIFF
    >>> channel_info = ['1.0.4_DAPI', '1.0.4_Cy3_iba1', '1.0.4_Cy5_Neun']
    >>> xml_path = create_ome_metadata_for_zarr(
    ...     "output.zarr",
    ...     channel_info,
    ...     template_tiff_path="template.tif"
    ... )
    
    >>> # Without template (minimal OME)
    >>> xml_path = create_ome_metadata_for_zarr(
    ...     "output.zarr",
    ...     channel_info,
    ...     size_x=2048,
    ...     size_y=2048
    ... )
    """
    if not OME_TYPES_AVAILABLE:
        raise ImportError("ome-types package is required. Install with: pip install ome-types")
    
    zarr_path = Path(zarr_path)
    
    # Step 1: Create or load OME template
    if template_tiff_path:
        print(f"Loading OME template from: {template_tiff_path}")
        ome = create_ome_from_template(template_tiff_path)
        if ome is None:
            print("Failed to load template. Creating minimal OME instead.")
            ome = create_minimal_ome(
                image_name=image_name or zarr_path.stem,
                size_x=size_x,
                size_y=size_y,
                size_c=len(channel_info),
                size_z=size_z,
                size_t=size_t,
                pixel_type=pixel_type
            )
    else:
        print("Creating minimal OME object...")
        ome = create_minimal_ome(
            image_name=image_name or zarr_path.stem,
            size_x=size_x,
            size_y=size_y,
            size_c=len(channel_info),
            size_z=size_z,
            size_t=size_t,
            pixel_type=pixel_type
        )
    
    # Step 2: Update with channel information
    print(f"Updating OME with {len(channel_info)} channels...")
    ome = update_ome_channels(ome, channel_info)
    
    # Step 3: Write to Zarr structure
    print(f"Writing metadata to: {zarr_path}")
    metadata_path = write_ome_xml_to_zarr(ome, zarr_path)
    
    return metadata_path


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if not OME_TYPES_AVAILABLE:
        print("Error: ome-types package is required")
        print("Install with: pip install ome-types")
        sys.exit(1)
    
    print("OME-Zarr Metadata Generator")
    print("=" * 70)
    print()
    
    # Example 1: Create minimal OME
    print("Example 1: Creating minimal OME object")
    print("-" * 70)
    channel_info = ['1.0.4_DAPI', '1.0.4_Cy3_iba1', '1.0.4_Cy5_Neun', '1.0.4_FITC_GFAP']
    
    ome = create_minimal_ome(
        image_name="Test_Image",
        size_x=2048,
        size_y=2048,
        size_c=len(channel_info)
    )
    
    print(f"Created OME with {len(ome.images)} image(s)")
    print(f"Image name: {ome.images[0].name}")
    print(f"Pixel dimensions: {ome.images[0].pixels.size_x} x {ome.images[0].pixels.size_y}")
    print(f"Initial channels: {ome.images[0].pixels.size_c}")
    
    # Example 2: Update channels
    print()
    print("Example 2: Updating channel names")
    print("-" * 70)
    
    ome = update_ome_channels(ome, channel_info)
    
    print(f"Updated channels: {ome.images[0].pixels.size_c}")
    for i, channel in enumerate(ome.images[0].pixels.channels):
        print(f"  Channel {i}: {channel.name}")
    
    # Example 3: Show XML output
    print()
    print("Example 3: Generated OME-XML (first 500 characters)")
    print("-" * 70)
    xml_string = ome.to_xml()
    print(xml_string[:500] + "...")
    
    print()
    print("=" * 70)
    print("To use with your Zarr files:")
    print("  1. Create your OME-Zarr file with your existing workflow")
    print("  2. Use create_ome_metadata_for_zarr() to add companion metadata")
    print("  3. Open in QuPath v6.0")
