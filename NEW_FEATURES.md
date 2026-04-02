# Features of CellDIVE Pipeline

Two major features have been added to enhance the pipeline's output and usability:

1. **Color Blind-Friendly Channel Colors** - Automatic assignment of high-contrast, accessible colors
2. **Magnification Metadata** - Configurable objective magnification with 20X default

---

## 1. Color Blind-Friendly Channel Colors

The pipeline now automatically assigns scientifically validated, color blind-friendly colors to all channels. These colors are based on:

- **Paul Tol's color schemes** (color blind safe palettes)
- **IBM's Design Color Blind Safe Palette**

### Color Assignments

| Channel Type | Color Name | Hex Code | Visual |
| -------------- | ------------ | ---------- | -------- |
| DAPI | White | `#FFFFFF` | ⚪ |
| Cy3 | Vibrant Orange | `#FFB000` | 🟠 |
| Cy5 | Magenta/Pink | `#DC267F` | 🟣 |
| Cy7 | Cyan | `#00FFFF` | 🔵 |
| FITC | Bright Green | `#00FF00` | 🟢 |

### Accessibility Benefits

✅ **Deuteranopia** (red-green color blindness, ~6% of males)
✅ **Protanopia** (red color blindness, ~2% of males)
✅ **Tritanopia** (blue-yellow color blindness, ~0.01% of population)
✅ **High contrast** for low vision users
✅ **Grayscale conversion** - colors remain distinguishable when printed in black & white

### Implementation

Colors are assigned in two places:

1. **In the Zarr file** - When creating the multi-channel array
2. **In the OME-XML metadata** - For QuPath visualization

```python
# Example from ome_metadata_enhanced.py
COLORBLIND_FRIENDLY_COLORS = {
    'DAPI': 'FFFFFF',      # White for nuclear stain
    'Cy3': 'FFB000',       # Vibrant orange
    'Cy5': 'DC267F',       # Magenta/pink
    'Cy7': '00FFFF',       # Cyan
    'FITC': '00FF00',      # Bright green
}
```

### How It Works

1. Channel name is parsed (e.g., "Cy3_iba1")
2. Fluorophore is identified ("Cy3")
3. Corresponding color is assigned (`#FFB000` - orange)
4. Color is embedded in both Zarr and OME-XML metadata

### Visual Comparison

**Before:** All channels displayed in red (`#FF0000`)
**After:** Each channel has a distinct, accessible color

---

## 2. Magnification Metadata

The pipeline now includes objective magnification in the OME-XML metadata files, making it easier to track imaging parameters and scale measurements in QuPath.

### Default Value

**20.0X** - Standard magnification for CellDIVE imaging systems

### Usage

#### Use Default (20X)

```bash
python pipeline.py /path/to/images
```

Output:

```rtf
Magnification:    20.0X (default: 20.0X)
```

#### Custom Magnification

```bash
# 40X objective
python pipeline.py /path/to/images --magnification 40

# 10X objective
python pipeline.py /path/to/images --magnification 10
```

#### Omit Magnification

```bash
# Set to 0 to exclude magnification metadata
python pipeline.py /path/to/images --magnification 0
```

Output:

```rtf
Magnification:    Not included in metadata
```

### Example

Magnification is added to the OME-XML structure:

```xml
<Instrument ID="Instrument:0">
  <Objective ID="Objective:0" NominalMagnification="20.0"/>
</Instrument>

<Image ID="Image:0">
  <ObjectiveSettings ID="Objective:0"/>
  ...
</Image>
```

### Benefits

- ✅ **QuPath integration** - Magnification appears in image properties
- ✅ **Scale bar accuracy** - Correct scaling for measurements
- ✅ **Documentation** - Track imaging parameters with data
- ✅ **Reproducibility** - Clear record of acquisition settings

---

## Modified Files

### 1. ome_metadata_enhanced.py

**New:**

- `COLORBLIND_FRIENDLY_COLORS` dictionary
- `assign_channel_color()` function
- `magnification` parameter in all functions
- Objective/ObjectiveSettings creation in OME metadata

**Key Changes:**

```python
def merge_ome_metadata_from_files(
    tiff_files: List[Union[str, Path]],
    channel_names: List[str],
    image_name: str = "Merged_Image",
    magnification: Optional[float] = 20.0  # NEW
) -> OME:
    # ...
    # Assign color blind-friendly color
    color_hex = assign_channel_color(display_name, i)  # NEW

    channel = Channel(
        id=f"Channel:0:{i}",
        name=display_name,
        samples_per_pixel=1,
        color=color_hex  # NEW
    )
    # ...
```

### 2. pipeline.py

**New:**

- `assign_channel_color` import
- `--magnification` / `-m` command-line argument
- Magnification display in output
- Color assignment in Zarr writer

**Key Changes:**

```python
# Parse arguments
parser.add_argument(
    '--magnification', '-m',
    type=float,
    default=20.0,
    help='Objective magnification (default: 20.0X)'
)

# Use colors in Zarr writer
color_hex = assign_channel_color(display_name, i)
channel_objects.append(
    Channel(label=display_name, color=color_hex)
)

# Pass to metadata function
create_metadata_for_merged_zarr(
    zarr_path=zarr_path,
    tiff_files=tiff_files,
    channel_names=channel_names,
    image_name=f"Region_{region_id}",
    magnification=magnification  # NEW
)
```

### 3. PIPELINE_README.md

**Updated sections:**

- Overview - mentions color blind-friendly colors
- Command-line options - includes `--magnification`
- New section: "Channel Color Assignments"
- New section: "Magnification Metadata"
- Updated "Opening in QuPath" section
- Updated "Metadata Preservation" section

---

## Usage Examples

### Example 1: Standard Processing (uses all new features)

```bash
python pipeline.py /path/to/images
```

Output:

```rtf
======================================================================
CellDIVE OME-TIFF to OME-Zarr Pipeline
======================================================================

Input directory:  /path/to/images
Output directory: /path/to/images/zarr_output
Pyramid levels:   5
Magnification:    20.0X (default: 20.0X)

...

Processing R000...
  Files: 4
  Channels: 4
  Creating OME-Zarr with 5 pyramid levels...
  Creating OME metadata from 4 source files...
  Using magnification: 20.0X (default: 20.0X)
  ✓ Successfully processed R000
```

Channels will display in QuPath with:

- DAPI: White
- Cy3_iba1: Orange
- Cy5_Neun: Magenta
- FITC_GFAP: Green

### Example 2: Custom Magnification

```bash
python pipeline.py /path/to/images --magnification 40
```

Output shows:

```rtf
Magnification:    40.0X (default: 20.0X)
```

### Example 3: Multiple Regions with Custom Settings

```bash
python pipeline.py /path/to/images \
  --regions R000 R001 R002 \
  --magnification 10 \
  --pyramid-levels 6 \
  --output /path/to/output
```

---

## Technical Details

### Color Selection Rationale

1. **DAPI → White**: Nuclear stain is fundamental; white provides maximum visibility
2. **Cy3 → Orange**: High contrast against blue/cyan channels
3. **Cy5 → Magenta**: Distinct from orange (Cy3) and red; visible to color blind individuals
4. **Cy7 → Cyan**: Complementary to magenta; far-red channel gets cool color
5. **FITC → Green**: Classic fluorophore; green is universally associated with FITC

### Default Color Fallback

If a channel doesn't match known fluorophores, colors are assigned cyclically from this palette:

```python
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
```

### Magnification Storage

The magnification value is stored in multiple OME-XML locations:

- **Objective.NominalMagnification** - The physical objective specification
- **ObjectiveSettings** - Links the image to the objective

This redundancy ensures compatibility with different OME-XML readers.

---

## Testing

Both features can be verified:

### Verify Colors

1. Open `.zarr` file in QuPath
2. Check channel colors in the channel panel
3. Verify high contrast between channels

### Verify Magnification

1. Open `.zarr` file in QuPath
2. View **Image → Show Image Properties**
3. Check for magnification value (20X or custom)
4. Verify scale bars use correct magnification

---

## Backward Compatibility

✅ **Fully backward compatible**

- Existing scripts continue to work
- Default values maintain previous behavior
- No breaking changes to function signatures
- All parameters are optional

---

## Future Enhancements

Possible future additions:

- Custom color maps via configuration file
- Per-channel magnification (for multi-objective workflows)
- Color scheme presets (scientific publisher requirements)
- Interactive color assignment tool

---

## References

**Color Blind Safe Palettes:**

- Paul Tol's Notes: <https://personal.sron.nl/~pault/>
- IBM Design Color Blind Safe Palette
- Wong, B. (2011). "Color blindness." Nature Methods 8(6): 441.

**OME-XML Specification:**

- OME Data Model: <https://docs.openmicroscopy.org/ome-model/>
- QuPath OME-Zarr Support: <https://qupath.readthedocs.io/>

---

## Questions?

For issues or questions about these features:

1. See [PIPELINE_README.md](PIPELINE_README.md) for detailed usage
2. Check [OME_METADATA_GUIDE.md](Claude_Code_Reference_Docs/OME_METADATA_GUIDE.md) for metadata details
3. Review example code in [pipeline.py](pipeline.py) and [ome_metadata_enhanced.py](ome_metadata_enhanced.py)
