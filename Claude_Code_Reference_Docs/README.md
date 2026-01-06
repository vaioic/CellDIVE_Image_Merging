# OME-TIFF File Grouping Function

## Overview

This Python module provides functions to group OME-TIFF microscopy image files by their region identifier (R###) and extract channel/marker information. The module uses regex pattern matching to parse filenames and organize them for downstream processing.

## Main Functions

### 1. `group_ome_tiff_by_region(directory, return_type="dict")`
Groups OME-TIFF files by their region identifier.

### 2. `extract_channel_marker_info(directory)`
Extracts round number, channel name, and marker information from filenames, organized by region.

## File Naming Convention

The function uses a **simplified regex pattern** that only requires three essential components to be present in the filename:

### Required Components:
1. **R###**: Region identifier with exactly 3 digits (e.g., R000, R001, R010, R999)
2. **FINAL**: The keyword "FINAL" must appear somewhere in the filename
3. **.ome.tif**: File must end with the .ome.tif extension

### Optional Components (Ignored by Pattern):
The pattern is **flexible** and ignores all other parts of the filename, including:
- prefix (initials, project codes, etc.)
- dates
- sample IDs
- round numbers
- channel names
- marker names
- suffixes

This makes the function work with various naming conventions as long as the three required components are present.

### Example Valid Filenames:
```
KK_10082025_S2_1.0.4_R000_Cy3_iba1_FINAL_AFR_F.ome.tif  ✓
Sample_R001_FINAL.ome.tif  ✓
FINAL_R002_test.ome.tif  ✓
any_prefix_R123_any_suffix_FINAL_anything.ome.tif  ✓
```

### Example Invalid Filenames:
```
KK_10082025_S2_1.0.4_R000_Cy3_iba1_AFR_F.ome.tif  ✗ (missing FINAL)
Sample_R001_FINAL.tif  ✗ (missing .ome extension)
Sample_FINAL.ome.tif  ✗ (missing R### region identifier)
```

## Installation

No additional packages required beyond Python 3.11 standard library:
- `re` (regex operations)
- `pathlib` (file path handling)
- `typing` (type hints)
- `collections` (defaultdict)

## Function Signatures

### 1. group_ome_tiff_by_region()

```python
def group_ome_tiff_by_region(
    directory: Union[str, Path],
    return_type: str = "dict"
) -> Union[Dict[str, List[str]], List[List[str]]]
```

Groups OME-TIFF files by their region identifier (R###).

**Parameters:**
- **directory** (str or Path): Path to the directory containing OME-TIFF files
- **return_type** (str, optional): Format of return value
  - `"dict"` (default): Returns dictionary with region IDs as keys
  - `"list"`: Returns list of lists, one per region

**Returns:**
- **Dict[str, List[str]]** if return_type="dict": Dictionary mapping region IDs to file paths
- **List[List[str]]** if return_type="list": List of file path lists, one per region

### 2. extract_channel_marker_info()

```python
def extract_channel_marker_info(
    directory: Union[str, Path]
) -> Dict[str, List[str]]
```

Extracts round number, channel name, and marker name from filenames, organized by region.

**Parameters:**
- **directory** (str or Path): Path to the directory containing OME-TIFF files

**Returns:**
- **Dict[str, List[str]]**: Dictionary with region IDs as keys and lists of formatted strings as values
  - Format for DAPI: `"round_DAPI"` (e.g., `"1.0.4_DAPI"`)
  - Format for other channels: `"round_channel_marker"` (e.g., `"1.0.4_Cy3_iba1"`)

**Expected Filename Patterns:**

For this function to work correctly, filenames should follow these patterns:
- **DAPI files**: `prefix_mmddyyyy_S#_round_R###_DAPI_FINAL_F.ome.tif`
- **Other channels**: `prefix_mmddyyyy_S#_round_R###_channel_marker_FINAL_AFR_F.ome.tif`

Where:
- `round`: Format like 1.0.4, 2.0.1, 15.0.4 (first number can be 1-15)
- `R###`: Region identifier (e.g., R000, R001)
- `channel`: DAPI, Cy3, Cy5, FITC, or Cy7
- `marker`: Alphanumeric name (not present for DAPI files)

**Example Output:**
```python
{
    'R000': ['1.0.4_DAPI', '1.0.4_Cy3_iba1', '1.0.4_Cy5_Neun', '1.0.4_FITC_GFAP'],
    'R001': ['1.0.4_DAPI', '1.0.4_Cy3_iba1', '2.0.1_DAPI', '2.0.1_Cy5_marker2'],
    'R002': ['3.0.2_DAPI', '3.0.2_Cy7_marker']
}
```

### 2. extract_channel_marker_info()

```python
def extract_channel_marker_info(
    directory: Union[str, Path]
) -> Dict[str, List[str]]
```

Extracts channel and marker information from OME-TIFF files, organized by region.

**Parameters:**
- **directory** (str or Path): Path to the directory containing OME-TIFF files

**Returns:**
- **Dict[str, List[str]]**: Dictionary with region IDs as keys and lists of channel/marker strings as values

**Format of returned strings:**
- For DAPI: `"1.0.4_DAPI"`
- For other channels: `"1.0.4_Cy3_iba1"` (format: round_channel_marker)

**Example Return:**
```python
{
    'R000': ['1.0.4_DAPI', '1.0.4_Cy3_iba1', '1.0.4_Cy5_Neun'],
    'R001': ['2.0.1_DAPI', '2.0.1_Cy3_marker1']
}
```

## Usage Examples

### Example 1: Basic File Grouping with Dictionary Return

```python
from group_ome_tiff_files import group_ome_tiff_by_region

# Group files by region
groups = group_ome_tiff_by_region("/path/to/images")

# Access files for a specific region
r000_files = groups["R000"]
print(f"Found {len(r000_files)} files for region R000")

# Iterate through all regions
for region_id, file_list in groups.items():
    print(f"{region_id}: {len(file_list)} files")
```

### Example 2: Extracting Channel and Marker Information

```python
from group_ome_tiff_files import extract_channel_marker_info

# Extract channel/marker info organized by region
channel_info = extract_channel_marker_info("/path/to/images")

# Output format:
# {
#     'R000': ['1.0.4_DAPI', '1.0.4_Cy3_iba1', '1.0.4_Cy5_Neun', ...],
#     'R001': ['1.0.4_DAPI', '1.0.4_Cy3_iba1', ...],
#     ...
# }

# Access info for a specific region
for info in channel_info["R000"]:
    print(info)
# Output:
#   1.0.4_DAPI
#   1.0.4_Cy3_iba1
#   1.0.4_Cy5_Neun
#   1.0.4_FITC_GFAP
```

### Example 3: Combined File and Channel/Marker Processing

```python
from group_ome_tiff_files import group_ome_tiff_by_region, extract_channel_marker_info

# Get both file paths and channel/marker info
file_groups = group_ome_tiff_by_region("/path/to/images")
channel_info = extract_channel_marker_info("/path/to/images")

# Process each region
for region_id in file_groups.keys():
    print(f"\nProcessing {region_id}:")
    print(f"  Files: {len(file_groups[region_id])}")
    print(f"  Channels: {len(channel_info[region_id])}")
    
    # Your processing code here
    for filepath, channel_marker in zip(file_groups[region_id], channel_info[region_id]):
        print(f"    {channel_marker}: {filepath}")
```

### Example 4: Parsing Channel/Marker Strings

```python
from group_ome_tiff_files import extract_channel_marker_info

channel_info = extract_channel_marker_info("/path/to/images")

for region_id, info_list in channel_info.items():
    print(f"\n{region_id}:")
    for info in info_list:
        parts = info.split('_')
        
        if len(parts) == 2:  # DAPI format: round_DAPI
            round_num = parts[0]
            channel = parts[1]
            print(f"  Round {round_num}: {channel} (no marker)")
        else:  # Other channels: round_channel_marker
            round_num = parts[0]
            channel = parts[1]
            marker = '_'.join(parts[2:])  # Rejoin in case marker has underscores
            print(f"  Round {round_num}: {channel} - Marker: {marker}")
```

### Example 5: Using List Return Type

```python
from group_ome_tiff_files import group_ome_tiff_by_region

# Get groups as list of lists
groups = group_ome_tiff_by_region("/path/to/images", return_type="list")

# Process each group
for i, file_list in enumerate(groups):
    print(f"Processing group {i+1} with {len(file_list)} files")
    # Your processing code here
```

### Example 6: Processing Each Region

```python
from group_ome_tiff_files import group_ome_tiff_by_region
from pathlib import Path

groups = group_ome_tiff_by_region("/path/to/images")

for region_id, file_paths in groups.items():
    print(f"\nProcessing region {region_id}")
    
    # Separate files by channel
    channel_files = {
        'DAPI': [],
        'Cy3': [],
        'Cy5': [],
        'FITC': [],
        'Cy7': []
    }
    
    for filepath in file_paths:
        filename = Path(filepath).name
        for channel in channel_files.keys():
            if channel in filename:
                channel_files[channel].append(filepath)
                break
    
    # Process each channel
    for channel, files in channel_files.items():
        if files:
            print(f"  {channel}: {len(files)} file(s)")
            # Your channel-specific processing here
```

### Example 7: Error Handling

```python
from group_ome_tiff_files import group_ome_tiff_by_region, extract_channel_marker_info

try:
    groups = group_ome_tiff_by_region("/path/to/images")
    channel_info = extract_channel_marker_info("/path/to/images")
    
    if not groups:
        print("No matching files found")
    else:
        print(f"Successfully grouped {len(groups)} regions")
        print(f"Extracted info for {len(channel_info)} regions")
        
except ValueError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Example 8: Filtering and Analysis

```python
from group_ome_tiff_files import group_ome_tiff_by_region, extract_channel_marker_info

groups = group_ome_tiff_by_region("/path/to/images")
channel_info = extract_channel_marker_info("/path/to/images")

# Find regions with complete channel sets
required_channels = {'DAPI', 'Cy3', 'Cy5', 'FITC'}

for region_id, info_list in channel_info.items():
    # Extract unique channels in this region
    channels_present = set()
    for info in info_list:
        parts = info.split('_')
        channel = parts[1] if len(parts) >= 2 else None
        if channel:
            channels_present.add(channel)
    
    # Check completeness
    if required_channels.issubset(channels_present):
        print(f"{region_id}: Complete ✓")
    else:
        missing = required_channels - channels_present
        print(f"{region_id}: Missing {missing}")
```

## Key Features

### File Grouping (`group_ome_tiff_by_region`)
1. **Regex-based parsing**: Robust pattern matching handles variations in naming
2. **FINAL filtering**: Automatically excludes non-final files
3. **Flexible return types**: Choose between dictionary or list format
4. **Sorted output**: Results are sorted by region ID for consistency
5. **Full path preservation**: Returns complete file paths for easy file access
6. **Agnostic to group count**: Handles any number of regions dynamically

### Channel/Marker Extraction (`extract_channel_marker_info`)
1. **Structured output**: Returns dictionary with region IDs as keys
2. **Format**: `{region_id: ["round_DAPI", "round_channel_marker", ...]}`
3. **DAPI handling**: Correctly identifies DAPI channels without markers
4. **Marker capture**: Captures full marker names including underscores
5. **Multiple rounds**: Handles files from different imaging rounds
6. **Flexible naming**: Works with various filename structures (region before/after round)

## Important Notes

1. **Required components only**: The pattern only checks for R###, FINAL, and .ome.tif
2. **Order independent**: R### and FINAL can appear in any order in the filename
3. **Case insensitive**: Pattern matching is case-insensitive
4. **Region format**: Must be exactly 3 digits (R000-R999)
5. **Flexible naming**: All other filename components are ignored
6. **Empty results**: If no matching files found, returns empty dict/list

## Testing

The package includes a comprehensive test script (`test_grouping.py`) that demonstrates:
- Dictionary and list return types
- File grouping by region
- Channel extraction
- Statistics generation

Run tests with:
```bash
python test_grouping.py
```

## Advanced Usage Examples

### Complete Workflow: Processing with Both File Paths and Metadata

```python
from group_ome_tiff_files import (
    group_ome_tiff_by_region,
    extract_channel_marker_info
)

# Get file paths and metadata
file_groups = group_ome_tiff_by_region("/path/to/images")
channel_info = extract_channel_marker_info("/path/to/images")

# Process each region
for region_id in file_groups.keys():
    print(f"\nProcessing {region_id}:")
    print(f"  Files: {len(file_groups[region_id])}")
    print(f"  Metadata: {channel_info.get(region_id, [])}")
    
    # Your image analysis pipeline here
    for filepath in file_groups[region_id]:
        # process_image(filepath)
        pass
```

### Parsing Channel/Marker Strings

```python
from group_ome_tiff_files import extract_channel_marker_info

channel_info = extract_channel_marker_info("/path/to/images")

for region_id, channels in channel_info.items():
    for channel_str in channels:
        parts = channel_str.split('_')
        round_num = parts[0]  # "1.0.4"
        channel = parts[1]     # "Cy3" or "DAPI"
        
        if len(parts) > 2:
            marker = '_'.join(parts[2:])
            print(f"{region_id}: Round {round_num}, {channel} → {marker}")
        else:
            print(f"{region_id}: Round {round_num}, {channel}")
```

## Troubleshooting

### No files found
- Verify the directory path is correct
- Check that files contain "FINAL" somewhere in their names (case-insensitive)
- Ensure files end with ".ome.tif" extension
- Verify filenames contain R### (R followed by exactly 3 digits)

### Missing regions
- Check that region IDs follow R### format with exactly 3 digits
- Verify the R prefix is present (lowercase 'r' works too due to case-insensitive matching)

### Incorrect grouping
- Ensure region IDs are consistent across related files
- Verify there are no typos in region identifiers (e.g., R01 vs R001)
- Remember: the pattern groups by R### only, not by any other filename component

## License

This code is provided as-is for research purposes.

## Version

Version 1.0 - Compatible with Python 3.11+
