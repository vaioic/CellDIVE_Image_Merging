# CellDIVE OME-TIFF to OME-Zarr Pipeline

Complete command-line pipeline for converting CellDIVE OME-TIFF microscopy images into multi-channel OME-Zarr files with QuPath-compatible metadata.

## Overview

This pipeline:
1. **Groups** OME-TIFF files by region identifier (R###)
2. **Merges** channels from multiple files into single multi-channel Zarr arrays
3. **Assigns color blind-friendly colors** to channels for optimal visualization
4. **Creates pyramids** for efficient visualization at multiple resolutions
5. **Preserves metadata** including exposure times, laser power, physical pixel sizes, and magnification
6. **Generates OME-XML** companion files for QuPath v6.0 compatibility

## Installation

### Required Packages

```bash
# Core dependencies
pip install bioio bioio-ome-zarr bioio-ome-tiff ome-types tifffile numpy

# Optional but recommended
pip install dask
```

### Verify Installation

```bash
python pipeline.py --help
```

## Quick Start

### Basic Usage

Process all regions in a directory:

```bash
python pipeline.py /path/to/your/ome-tiff-files
```

This creates a `zarr_output` subdirectory with `.zarr` files for each region.

### Specify Output Directory

```bash
python pipeline.py /path/to/images --output /path/to/output
```

### Process Specific Regions

```bash
python pipeline.py /path/to/images --regions R000 R001 R002
```

### Customize Pyramid Levels

```bash
python pipeline.py /path/to/images --pyramid-levels 6
```

### Dry Run (Preview Without Creating Files)

```bash
python pipeline.py /path/to/images --dry-run
```

## File Naming Convention

The pipeline expects OME-TIFF files following this naming convention:

### DAPI Files
```
prefix_mmddyyyy_S#_round_R###_DAPI_FINAL_F.ome.tif
```

### Other Channels
```
prefix_mmddyyyy_S#_round_R###_channel_marker_FINAL_AFR_F.ome.tif
```

### Required Components
- `R###` - Region identifier (e.g., R000, R001)
- `FINAL` - Must appear in filename
- `.ome.tif` - File extension

### Supported Channels
- DAPI (no marker)
- Cy3, Cy5, Cy7, FITC (with marker)

### Example Filenames
```
KK_10082025_S2_1.0.4_R000_DAPI_FINAL_F.ome.tif
KK_10082025_S2_1.0.4_R000_Cy3_iba1_FINAL_AFR_F.ome.tif
KK_10082025_S2_1.0.4_R000_Cy5_Neun_FINAL_AFR_F.ome.tif
KK_10082025_S2_1.0.4_R000_FITC_GFAP_FINAL_AFR_F.ome.tif
```

## Output Structure

After processing, each region will have a corresponding `.zarr` directory:

```
output_directory/
    R000.zarr/
        OME/
            .zgroup           ← Zarr group indicator
            METADATA.ome.xml  ← Companion metadata for QuPath
        0/                    ← Full resolution (C, Y, X)
        1/                    ← Level 1 (2x downsampled)
        2/                    ← Level 2 (4x downsampled)
        3/                    ← Level 3 (8x downsampled)
        4/                    ← Level 4 (12x downsampled)
        .zattrs               ← Zarr metadata
        .zgroup               ← Zarr group file
    R001.zarr/
        ...
```

## Command-Line Options

```
usage: pipeline.py [-h] [--output OUTPUT] [--regions REGIONS [REGIONS ...]]
                   [--pyramid-levels PYRAMID_LEVELS] [--magnification MAGNIFICATION]
                   [--dry-run] [--verbose]
                   input_directory

positional arguments:
  input_directory       Directory containing OME-TIFF files

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Output directory for Zarr files (default: input_directory/zarr_output)
  --regions REGIONS [REGIONS ...], -r REGIONS [REGIONS ...]
                        Specific region IDs to process (e.g., R000 R001)
  --pyramid-levels PYRAMID_LEVELS, -p PYRAMID_LEVELS
                        Number of pyramid levels to create (default: 5)
  --magnification MAGNIFICATION, -m MAGNIFICATION
                        Objective magnification (default: 20.0X). Set to 0 to omit.
  --chunk-size CHUNK_SIZE
                        Zarr chunk size in pixels (default: auto-calculated for ~32MB chunks)
  --compression {blosc,zstd,lz4,none}
                        Compression algorithm (default: blosc)
  --compression-level 1-9
                        Compression level 1-9 (default: 5)
  --workers WORKERS     Number of parallel workers (default: auto-detect CPU count)
  --dry-run             Show what would be processed without creating files
  --verbose, -v         Verbose output
```

**Performance Options** - See [PERFORMANCE_GUIDE.md](PERFORMANCE_GUIDE.md) for detailed optimization strategies.

## Complete Examples

### Example 1: Process All Regions

```bash
python pipeline.py E:/Images/CellDIVE_Experiment_01
```

Output:
```
output_directory/
    R000.zarr/
    R001.zarr/
    R002.zarr/
    ...
```

### Example 2: Process to Custom Location

```bash
python pipeline.py E:/Images/Raw --output E:/Images/Processed
```

### Example 3: Process Specific Regions with Custom Pyramids

```bash
python pipeline.py /data/images --regions R000 R005 R010 --pyramid-levels 6
```

### Example 4: Preview Processing

```bash
python pipeline.py /data/images --dry-run --verbose
```

This shows what would be processed without creating any files.

## Opening in QuPath

### QuPath v6.0

1. **Open QuPath v6.0**
2. **Drag and drop** a `.zarr` folder into QuPath, OR
3. **File > Open** and select a `.zarr` folder

QuPath will automatically:
- Read the `OME/METADATA.ome.xml` file for channel information
- Display all channels with correct names (e.g., "DAPI", "Cy3_iba1")
- Show channels in **color blind-friendly colors** for optimal visualization
- Load the multi-resolution pyramid for smooth navigation
- Preserve physical pixel sizes for measurements
- Display magnification information (20X by default)

### Verifying Metadata

In QuPath, check that:
- All channels appear with correct names
- Channels display in high-contrast, color blind-friendly colors
- Channel count matches your input files
- Physical pixel sizes are preserved (check Properties)
- Magnification is shown correctly (if included)

## Channel Color Assignments

The pipeline automatically assigns **color blind-friendly colors** to channels based on Paul Tol's color schemes and IBM's accessible palette:

| Channel | Color | Hex Code | Description |
|---------|-------|----------|-------------|
| DAPI | White | `#FFFFFF` | Nuclear stain |
| Cy3 | Vibrant Orange | `#FFB000` | High contrast |
| Cy5 | Magenta | `#DC267F` | Distinct from Cy3 |
| Cy7 | Cyan | `#00FFFF` | Complementary |
| FITC | Bright Green | `#00FF00` | Classic fluorophore |

**Benefits:**
- ✅ High contrast between channels
- ✅ Distinguishable for deuteranopia (red-green color blindness)
- ✅ Distinguishable for protanopia (red color blindness)
- ✅ Distinguishable for tritanopia (blue-yellow color blindness)
- ✅ Consistent across all visualizations

## Magnification Metadata

The pipeline includes magnification metadata in the OME-XML files:

**Default:** 20.0X (commonly used for CellDIVE imaging)

### Custom Magnification

```bash
# Use 40X magnification
python pipeline.py /path/to/images --magnification 40

# Use 10X magnification
python pipeline.py /path/to/images --magnification 10

# Omit magnification metadata
python pipeline.py /path/to/images --magnification 0
```

The magnification is displayed during processing:
```
Magnification:    20.0X (default: 20.0X)
```

## Metadata Preservation

The pipeline preserves the following metadata from source OME-TIFF files:

✅ **Channel names** - Extracted from filenames and added to metadata
✅ **Channel colors** - Color blind-friendly palette assigned automatically
✅ **Magnification** - Objective magnification (default 20X)
✅ **Physical pixel sizes** - X, Y dimensions in micrometers
✅ **Exposure times** - Per-channel acquisition exposure
✅ **Laser power** - Light source settings if available
✅ **Excitation/Emission wavelengths** - Channel-specific wavelengths
✅ **Detector settings** - Camera/detector parameters

## Troubleshooting

### Issue: No files found

**Error:**
```
Error: No OME-TIFF files found matching the naming convention
```

**Solution:**
- Verify files contain `R###`, `FINAL`, and end with `.ome.tif`
- Check that files are in the specified directory
- Use `--verbose` to see what's being searched

### Issue: xmlns:schemaLocation error

**Error:**
```
XMLSyntaxError: xmlns:schemaLocation is not a valid URI
```

**Solution:**
The pipeline automatically handles this error by fixing schema issues in the source OME-TIFF files. If you still see this error, the enhanced metadata module will create minimal OME metadata instead.

### Issue: Channel count mismatch

**Error:**
```
Error: File count (4) doesn't match channel count (3)
```

**Solution:**
- Ensure all channels for a region have matching files
- Check filename patterns match the expected convention
- Verify all files contain the `FINAL` keyword

### Issue: Memory errors

**Error:**
```
MemoryError: Unable to allocate array
```

**Solution:**
- Process regions one at a time using `--regions R000`
- Reduce workers: `--workers 2`
- Reduce `--pyramid-levels` to fewer levels
- Use smaller chunks: `--chunk-size 256`
- Close other applications to free memory
- Consider processing on a machine with more RAM

### Issue: Slow processing

**Solution:**
- Increase workers: `--workers 16`
- Reduce compression: `--compression-level 1` or `--compression none`
- Use faster compression: `--compression lz4`
- See [PERFORMANCE_GUIDE.md](PERFORMANCE_GUIDE.md) for detailed optimization

### Issue: Import errors

**Error:**
```
ImportError: No module named 'bioio'
```

**Solution:**
```bash
pip install bioio bioio-ome-zarr bioio-ome-tiff ome-types tifffile
```

## Performance Tips

### Processing Large Datasets

1. **Process in batches** - Use `--regions` to process a few regions at a time
2. **Monitor memory** - Each region loads all channels into memory
3. **Use SSD storage** - Significantly faster than HDD for Zarr writes
4. **Adjust pyramid levels** - Fewer levels = faster processing

### Recommended Settings

For typical CellDIVE images (4-6 channels, ~50K x 60K pixels):

```bash
# Good balance of speed and quality
python pipeline.py /data/images --pyramid-levels 5

# Faster processing, fewer zoom levels
python pipeline.py /data/images --pyramid-levels 3

# Maximum quality, slower
python pipeline.py /data/images --pyramid-levels 7
```

## Integration with Existing Workflows

### Using Pipeline Components Separately

The pipeline consists of modular components you can use independently:

#### 1. Group Files Only

```python
from Group_Files import group_ome_tiff_by_region, extract_channel_marker_info

file_groups = group_ome_tiff_by_region("/path/to/images")
channel_info = extract_channel_marker_info("/path/to/images")
```

#### 2. Create Zarr Only

```python
from pipeline import create_zarr_from_tiff_group

create_zarr_from_tiff_group(
    tiff_files=["file1.ome.tif", "file2.ome.tif"],
    channel_names=["1.0.4_DAPI", "1.0.4_Cy3_iba1"],
    output_path=Path("output.zarr"),
    pyramid_levels=5
)
```

#### 3. Add Metadata to Existing Zarr

```python
from ome_metadata_enhanced import create_metadata_for_merged_zarr

create_metadata_for_merged_zarr(
    zarr_path="existing.zarr",
    tiff_files=["source1.ome.tif", "source2.ome.tif"],
    channel_names=["DAPI", "Cy3_iba1"],
    image_name="Region_R000"
)
```

## Python API Usage

### In a Python Script

```python
from pathlib import Path
from Group_Files import group_ome_tiff_by_region, extract_channel_marker_info
from pipeline import process_region

# Setup
input_dir = Path("/data/images")
output_dir = Path("/data/output")
output_dir.mkdir(exist_ok=True)

# Get file groups
file_groups = group_ome_tiff_by_region(input_dir)
channel_info = extract_channel_marker_info(input_dir)

# Process each region
for region_id in file_groups.keys():
    success = process_region(
        region_id=region_id,
        tiff_files=file_groups[region_id],
        channel_names=channel_info[region_id],
        output_dir=output_dir,
        pyramid_levels=5,
        dry_run=False
    )

    if success:
        print(f"✓ Processed {region_id}")
    else:
        print(f"✗ Failed {region_id}")
```

### In a Jupyter Notebook

```python
# Cell 1: Imports
from pathlib import Path
from Group_Files import group_ome_tiff_by_region, extract_channel_marker_info
from pipeline import process_region

# Cell 2: Configuration
input_dir = Path("E:/Images/Experiment")
output_dir = Path("E:/Images/Output")
output_dir.mkdir(exist_ok=True)

# Cell 3: Group files
file_groups = group_ome_tiff_by_region(input_dir)
channel_info = extract_channel_marker_info(input_dir)

print(f"Found {len(file_groups)} regions")
for region_id, files in file_groups.items():
    print(f"{region_id}: {len(files)} files")

# Cell 4: Process one region
region_id = "R000"
process_region(
    region_id=region_id,
    tiff_files=file_groups[region_id],
    channel_names=channel_info[region_id],
    output_dir=output_dir,
    pyramid_levels=5
)
```

## Support

For issues, questions, or feature requests, please refer to:
- **Project Documentation**: See [PROJECT_SUMMARY.md](Claude_Code_Reference_Docs/PROJECT_SUMMARY.md)
- **Metadata Guide**: See [OME_METADATA_GUIDE.md](Claude_Code_Reference_Docs/OME_METADATA_GUIDE.md)

## Version History

- **v1.0** - Initial pipeline release
  - Complete OME-TIFF to OME-Zarr conversion
  - Multi-resolution pyramid generation
  - Metadata preservation
  - QuPath v6.0 compatibility

## License

This code is provided as-is for research purposes.
