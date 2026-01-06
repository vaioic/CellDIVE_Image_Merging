# OME-TIFF File Processing and OME-Zarr Metadata Generation

## Project Overview

This project provides a complete workflow for processing microscopy OME-TIFF files:
1. Group image files by region identifier
2. Extract channel and marker metadata from filenames
3. Generate OME.XML companion metadata for OME-Zarr files (QuPath v6.0 compatible)

## Files in This Project

### Core Modules

1. **group_ome_tiff_files.py**
   - Groups OME-TIFF files by region identifier (R###)
   - Extracts channel and marker information from filenames
   - Main functions:
     - `group_ome_tiff_by_region(directory)` - Returns dict of {region_id: [file_paths]}
     - `extract_channel_marker_info(directory)` - Returns dict of {region_id: ['round_channel_marker', ...]}

2. **ome_zarr_metadata.py**
   - Generates OME.XML metadata for OME-Zarr files
   - Creates companion METADATA.ome.xml for QuPath v6.0
   - Main functions:
     - `create_ome_from_template(tiff_path)` - Load OME from template TIFF (with auto schema fixing)
     - `create_minimal_ome()` - Create minimal OME from scratch
     - `update_ome_channels(ome, channel_info)` - Update channel names
     - `write_ome_xml_to_zarr(ome, zarr_path)` - Write to correct Zarr location
     - `create_ome_metadata_for_zarr()` - High-level wrapper function

3. **workflow_example.py**
   - Complete integration examples
   - Shows how to combine file grouping with metadata generation
   - Demonstrates full pipeline from raw TIFFs to Zarr with metadata

### Documentation

4. **README.md**
   - Complete documentation for file grouping functions
   - Usage examples and API reference

5. **OME_METADATA_GUIDE.md**
   - Detailed guide for OME metadata generation
   - Troubleshooting for common issues (xmlns:schemaLocation error)
   - Integration examples

### Test Files

6. **test_grouping.py** - Tests for basic file grouping
7. **test_flexibility.py** - Tests for flexible filename patterns
8. **test_channel_marker.py** - Tests for channel/marker extraction

## Quick Start

### Installation

```bash
# Required packages
pip install ome-types tifffile --break-system-packages

# Optional: for your existing Zarr creation workflow
pip install zarr ome-zarr --break-system-packages
```

### Basic Usage

```python
from group_ome_tiff_files import group_ome_tiff_by_region, extract_channel_marker_info
from ome_zarr_metadata import create_ome_metadata_for_zarr

# Step 1: Group files by region
file_groups = group_ome_tiff_by_region("/path/to/images")
# Returns: {'R000': [files...], 'R001': [files...], ...}

# Step 2: Extract channel/marker info
channel_info = extract_channel_marker_info("/path/to/images")
# Returns: {'R000': ['1.0.4_DAPI', '1.0.4_Cy3_iba1', ...], ...}

# Step 3: Create OME-Zarr (your existing workflow)
# create_your_zarr_file(file_groups['R000'], 'R000.zarr')

# Step 4: Add companion metadata for QuPath
create_ome_metadata_for_zarr(
    zarr_path="R000.zarr",
    channel_info=channel_info['R000'],
    size_x=2048,
    size_y=2048
)
```

## File Naming Convention

The scripts expect OME-TIFF files with these patterns:

**For DAPI files:**
```
prefix_mmddyyyy_S#_round_R###_DAPI_FINAL_F.ome.tif
```

**For other channels:**
```
prefix_mmddyyyy_S#_round_R###_channel_marker_FINAL_AFR_F.ome.tif
```

**Required components:**
- R### - Region identifier (e.g., R000, R001)
- FINAL - Must appear in filename
- .ome.tif - File extension

**Supported channels:**
- DAPI (no marker)
- Cy3, Cy5, Cy7, FITC (with marker)

**Example filenames:**
```
KK_10082025_S2_1.0.4_R000_DAPI_FINAL_F.ome.tif
KK_10082025_S2_1.0.4_R000_Cy3_iba1_FINAL_AFR_F.ome.tif
KK_10082025_S2_1.0.4_R001_FITC_GFAP_FINAL_AFR_F.ome.tif
```

## Complete Workflow Example

```python
from pathlib import Path
from group_ome_tiff_files import group_ome_tiff_by_region, extract_channel_marker_info
from ome_zarr_metadata import create_ome_metadata_for_zarr

# Configuration
image_directory = "/path/to/raw/images"
output_directory = "/path/to/output/zarrs"

# Get file groups and metadata
file_groups = group_ome_tiff_by_region(image_directory)
channel_info = extract_channel_marker_info(image_directory)

# Process each region
for region_id in file_groups.keys():
    print(f"Processing {region_id}...")
    
    # Get data for this region
    region_files = file_groups[region_id]
    region_channels = channel_info[region_id]
    
    # Define output path
    zarr_path = Path(output_directory) / f"{region_id}.zarr"
    
    # YOUR CODE: Create OME-Zarr file
    # create_ome_zarr(region_files, zarr_path, ...)
    
    # Add companion metadata for QuPath
    create_ome_metadata_for_zarr(
        zarr_path=zarr_path,
        channel_info=region_channels,
        size_x=2048,
        size_y=2048,
        pixel_type="uint16"
    )
    
    print(f"✓ {region_id} complete")
```

## Output Structure

After processing, your Zarr files will have this structure:

```
R000.zarr/
    OME/
        .zgroup           ← Zarr group indicator
        METADATA.ome.xml  ← Companion metadata for QuPath
    0/                    ← Your Zarr image data
    .zattrs
    .zgroup
```

## Key Features

### File Grouping (group_ome_tiff_files.py)

✅ **Flexible pattern matching** - Only requires R###, FINAL, and .ome.tif  
✅ **Automatic grouping** - Groups files by region identifier  
✅ **Channel extraction** - Parses channel and marker names from filenames  
✅ **Dictionary output** - Easy to iterate and process  

### Metadata Generation (ome_zarr_metadata.py)

✅ **Auto schema fixing** - Handles xmlns:schemaLocation errors automatically  
✅ **Template support** - Can load metadata from microscope TIFF files  
✅ **Minimal creation** - Can generate metadata without template  
✅ **Channel updating** - Loops through and updates all channels  
✅ **Correct location** - Writes to zarr_file/OME/METADATA.ome.xml  
✅ **.zgroup creation** - Automatically creates required Zarr group file  
✅ **QuPath compatible** - Tested with QuPath v6.0  

## Common Issues and Solutions

### Issue: xmlns:schemaLocation is not a valid URI

**Solution:**
```python
# Option 1: Use auto-fixing (default)
from ome_zarr_metadata import create_ome_from_template
ome = create_ome_from_template("template.tif", fix_schema=True)

# Option 2: Skip template
create_ome_metadata_for_zarr(zarr_path, channel_info)  # No template
```

### Issue: Package not installed

**Solution:**
```bash
pip install ome-types tifffile --break-system-packages
```

### Issue: QuPath can't read metadata

**Check:**
1. File exists at: `zarr_file/OME/METADATA.ome.xml`
2. Using QuPath v6.0 or later
3. .zgroup file was created

## Testing

Run the included tests to verify everything works:

```bash
# Test file grouping
python test_grouping.py

# Test flexible patterns
python test_flexibility.py

# Test channel extraction
python test_channel_marker.py
```

## Development Notes

### Python Version
- Developed for Python 3.11
- Uses only standard library plus:
  - ome-types (for OME metadata)
  - tifffile (for TIFF reading)

### Design Decisions

1. **Dictionary format only** - Simplified API based on user requirements
2. **Automatic schema fixing** - Handles common microscope export issues
3. **Minimal dependencies** - Uses standard library where possible
4. **Clear separation** - File grouping and metadata generation are independent modules

### Extension Points

To integrate with your existing Zarr creation workflow, add your code here:

```python
for region_id, files in file_groups.items():
    zarr_path = f"{region_id}.zarr"
    
    # INSERT YOUR ZARR CREATION CODE HERE
    # For example:
    # import ome_zarr
    # create_ome_zarr_pyramid(files, zarr_path)
    
    # Then add metadata
    create_ome_metadata_for_zarr(zarr_path, channel_info[region_id])
```

## Support

For detailed documentation, see:
- **README.md** - File grouping documentation
- **OME_METADATA_GUIDE.md** - Metadata generation guide

## License

This code is provided as-is for research purposes.

## Version History

- v1.0 - Initial implementation
  - File grouping by region
  - Channel/marker extraction
  - OME metadata generation
  - QuPath v6.0 compatibility
