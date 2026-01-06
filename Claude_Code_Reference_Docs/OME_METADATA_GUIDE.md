# OME-Zarr Metadata Generation Guide

## Quick Start

If you just want to add metadata to an existing Zarr file:

```python
from ome_zarr_metadata import create_ome_metadata_for_zarr

# Your channel info from extract_channel_marker_info()
channel_info = ['1.0.4_DAPI', '1.0.4_Cy3_iba1', '1.0.4_Cy5_Neun']

# Add metadata to your Zarr file
create_ome_metadata_for_zarr(
    zarr_path="R001.zarr",
    channel_info=channel_info,
    size_x=2048,  # Your image width
    size_y=2048   # Your image height
)
```

This creates the companion `METADATA.ome.xml` file that QuPath needs.

---

## Addressing Your Specific Issues

### Issue 1: xmlns:schemaLocation Error

**Problem:** `"xmlns:schemaLocation is not a valid URI"`

**Why this happens:** Some microscope software exports OME-XML with incorrect namespace declarations.

**Solutions:**

#### Solution A: Automatic fixing (recommended)
```python
from ome_zarr_metadata import create_ome_from_template

# The fix_schema=True parameter (default) attempts to fix this automatically
ome = create_ome_from_template("microscope_export.tif", fix_schema=True)
```

#### Solution B: Skip template entirely
```python
# Don't use a template - create minimal OME instead
create_ome_metadata_for_zarr(
    zarr_path="R001.zarr",
    channel_info=channel_info,
    size_x=2048,
    size_y=2048
    # No template_tiff_path parameter
)
```

#### Solution C: Manually fix the XML
1. Export OME-XML from your microscope software
2. Open in a text editor
3. Find: `xmlns:schemaLocation`
4. Replace with: `xsi:schemaLocation`
5. Ensure this line exists in the `<OME>` tag:
   ```xml
   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
   ```

---

### Issue 2: Editing Channel Names

**How to update channels:**

```python
from ome_zarr_metadata import update_ome_channels

# Channel info from your files
channel_info = [
    '1.0.4_DAPI',
    '1.0.4_Cy3_iba1',
    '1.0.4_Cy5_Neun',
    '1.0.4_FITC_GFAP'
]

# Update the OME object
ome = update_ome_channels(ome, channel_info)

# Check the result
for i, channel in enumerate(ome.images[0].pixels.channels):
    print(f"Channel {i}: {channel.name}")
# Output:
# Channel 0: DAPI
# Channel 1: Cy3_iba1
# Channel 2: Cy5_Neun
# Channel 3: FITC_GFAP
```

**Manual editing (if needed):**

```python
# Access the image and pixels
image = ome.images[0]
pixels = image.pixels

# Edit existing channel
pixels.channels[0].name = "DAPI"

# Add a new channel
from ome_types.model import Channel
new_channel = Channel(
    id=f"Channel:0:{len(pixels.channels)}",
    name="Cy7_marker",
    samples_per_pixel=1
)
pixels.channels.append(new_channel)

# Update the count
pixels.size_c = len(pixels.channels)
```

---

### Issue 3: Writing to Zarr Structure

**Correct location:** `file.zarr/OME/METADATA.ome.xml`

```python
from ome_zarr_metadata import write_ome_xml_to_zarr

# This creates the correct structure automatically
metadata_path = write_ome_xml_to_zarr(
    ome,
    zarr_path="R001.zarr",
    create_zgroup=True  # Also creates .zgroup file
)
```

**What gets created:**
```
R001.zarr/
    OME/
        .zgroup           ← Zarr group indicator
        METADATA.ome.xml  ← Your metadata for QuPath
    0/                    ← Your existing Zarr data
    .zattrs
    .zgroup
```

**About .zgroup:**
The `.zgroup` file is created automatically. It's a JSON file that tells Zarr this is a group:
```json
{"zarr_format": 2}
```

---

## Complete Integration Example

Here's how to integrate this with your existing workflow:

```python
from pathlib import Path
from group_ome_tiff_files import group_ome_tiff_by_region, extract_channel_marker_info
from ome_zarr_metadata import create_ome_metadata_for_zarr

# Your image directory
image_dir = "/path/to/images"
output_dir = "/path/to/output"

# Step 1: Get file groups and channel info
file_groups = group_ome_tiff_by_region(image_dir)
channel_info = extract_channel_marker_info(image_dir)

# Step 2: Process each region
for region_id, files in file_groups.items():
    print(f"Processing {region_id}...")
    
    # Define output path
    zarr_path = Path(output_dir) / f"{region_id}.zarr"
    
    # YOUR EXISTING CODE: Create OME-Zarr from files
    # create_your_zarr_file(files, zarr_path)
    
    # NEW CODE: Add companion metadata for QuPath
    create_ome_metadata_for_zarr(
        zarr_path=zarr_path,
        channel_info=channel_info[region_id],
        size_x=2048,     # Adjust to your image size
        size_y=2048,     # Adjust to your image size
        size_z=1,        # Number of Z slices
        size_t=1,        # Number of time points
        pixel_type="uint16"  # Your pixel type
    )
    
    print(f"✓ {region_id} complete with metadata")
```

---

## Workflow Options

### Option 1: With Template TIFF (Preserves Microscope Metadata)

```python
create_ome_metadata_for_zarr(
    zarr_path="R001.zarr",
    channel_info=channel_info,
    template_tiff_path="microscope_export.tif"  # Use one of your original TIFFs
)
```

**Pros:**
- Preserves original microscope metadata
- More complete metadata

**Cons:**
- May have schema errors
- Requires fixing

### Option 2: Without Template (Minimal Metadata)

```python
create_ome_metadata_for_zarr(
    zarr_path="R001.zarr",
    channel_info=channel_info,
    size_x=2048,
    size_y=2048
    # No template
)
```

**Pros:**
- No schema errors
- Simple and reliable

**Cons:**
- Minimal metadata only
- No microscope-specific info

---

## Verification

After creating your metadata, verify the structure:

```python
from pathlib import Path

zarr_path = Path("R001.zarr")

# Check that files exist
ome_dir = zarr_path / "OME"
metadata_file = ome_dir / "METADATA.ome.xml"
zgroup_file = ome_dir / ".zgroup"

print(f"OME directory exists: {ome_dir.exists()}")
print(f"Metadata file exists: {metadata_file.exists()}")
print(f".zgroup file exists: {zgroup_file.exists()}")

# Read and check metadata
if metadata_file.exists():
    from ome_types import from_xml
    
    with open(metadata_file, 'r') as f:
        xml_string = f.read()
    
    ome = from_xml(xml_string)
    print(f"Number of images: {len(ome.images)}")
    print(f"Number of channels: {ome.images[0].pixels.size_c}")
    
    for i, ch in enumerate(ome.images[0].pixels.channels):
        print(f"  Channel {i}: {ch.name}")
```

---

## Common Issues and Solutions

### Issue: Package not installed
```
ImportError: ome-types package is required
```

**Solution:**
```bash
pip install ome-types --break-system-packages
```

### Issue: tifffile needed for schema fixing
```
ImportError: tifffile package required
```

**Solution:**
```bash
pip install tifffile --break-system-packages
```

### Issue: Metadata file not created
**Check:**
1. Zarr directory exists before calling the function
2. You have write permissions
3. No errors printed during execution

### Issue: QuPath can't read metadata
**Check:**
1. File is at correct location: `zarr_file/OME/METADATA.ome.xml`
2. File is valid XML (open in text editor)
3. Using QuPath v6.0 or later

---

## Testing Your Setup

Test with a simple example:

```python
from pathlib import Path
from ome_zarr_metadata import create_minimal_ome, update_ome_channels, write_ome_xml_to_zarr

# Create a test Zarr directory
test_zarr = Path("test.zarr")
test_zarr.mkdir(exist_ok=True)

# Create minimal OME
ome = create_minimal_ome(
    image_name="Test",
    size_x=1024,
    size_y=1024,
    size_c=3
)

# Update with channels
channel_info = ['1.0.4_DAPI', '1.0.4_Cy3_iba1', '1.0.4_Cy5_Neun']
ome = update_ome_channels(ome, channel_info)

# Write to Zarr
metadata_path = write_ome_xml_to_zarr(ome, test_zarr)

print(f"Test successful! Metadata at: {metadata_path}")
print(f"You can now try opening {test_zarr} in QuPath")
```

---

## Next Steps

1. **Install required packages:**
   ```bash
   pip install ome-types tifffile --break-system-packages
   ```

2. **Test with one region first:**
   - Create one Zarr file with your existing workflow
   - Add metadata using `create_ome_metadata_for_zarr()`
   - Open in QuPath to verify

3. **Integrate into your pipeline:**
   - Add metadata generation after Zarr creation
   - Process all regions

4. **Verify in QuPath:**
   - Open the Zarr file
   - Check that channel names appear correctly
   - Confirm metadata is readable
