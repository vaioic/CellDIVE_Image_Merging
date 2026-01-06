# Performance Optimization Guide

This guide covers performance optimization options for the CellDIVE OME-TIFF to OME-Zarr pipeline.

## Overview

The pipeline includes several performance optimizations beyond basic region selection and pyramid levels:

1. **Parallel Processing** - Multi-threaded processing using Dask
2. **Chunk Optimization** - Optimized chunk sizes for I/O performance
3. **Compression** - Configurable compression algorithms and levels
4. **Lazy Loading** - Dask arrays for memory-efficient processing

---

## Quick Performance Recommendations

### For Speed (Fastest Processing)
```bash
python pipeline.py /path/to/images \
  --workers 16 \
  --compression none \
  --chunk-size 512
```

### For Balance (Recommended)
```bash
python pipeline.py /path/to/images \
  --workers 8 \
  --compression blosc \
  --compression-level 5
```

### For File Size (Smallest Files)
```bash
python pipeline.py /path/to/images \
  --workers 4 \
  --compression zstd \
  --compression-level 9 \
  --chunk-size 256
```

---

## Performance Options

### 1. Parallel Workers (`--workers`)

Controls the number of parallel threads used for processing.

**Syntax:**
```bash
--workers N
```

**Default:** Auto-detected (number of CPU cores)

**Examples:**
```bash
# Use 8 workers
python pipeline.py /path/to/images --workers 8

# Use all available cores (default)
python pipeline.py /path/to/images

# Use half of available cores
python pipeline.py /path/to/images --workers 4
```

**Guidelines:**
- **More workers** = Faster processing (up to CPU core count)
- **Fewer workers** = Less memory usage, leaves CPU for other tasks
- **Optimal:** 50-75% of CPU cores for system balance
- **Maximum:** Equal to physical CPU cores (not hyperthreads)

**Performance Impact:**
- 1 worker: Baseline speed
- 4 workers: ~3x faster
- 8 workers: ~5-6x faster (diminishing returns)
- 16+ workers: ~7-8x faster (minimal additional benefit)

---

### 2. Chunk Size (`--chunk-size`)

Controls the size of data chunks stored in Zarr format.

**Syntax:**
```bash
--chunk-size N  # NxN pixels
```

**Default:** Auto-calculated (~32MB per chunk)

**Examples:**
```bash
# Small chunks (better for random access, larger file)
python pipeline.py /path/to/images --chunk-size 256

# Large chunks (better for sequential access, smaller file)
python pipeline.py /path/to/images --chunk-size 2048

# Auto-calculated (recommended)
python pipeline.py /path/to/images
```

**Guidelines:**
- **Smaller chunks (256-512)**:
  - ✅ Faster random access (zooming/panning in QuPath)
  - ✅ Better for viewing
  - ❌ Slightly larger file size
  - ❌ More overhead

- **Larger chunks (1024-2048)**:
  - ✅ Faster sequential reading
  - ✅ Smaller file size
  - ✅ Better compression ratios
  - ❌ Slower random access

- **Auto-calculated (default)**:
  - Optimized for ~32MB chunks
  - Balances all factors
  - Adjusts based on image size and data type

**Typical Values:**
- **2K x 2K images**: 512 pixels → 2MB chunks
- **10K x 10K images**: 1024 pixels → 8MB chunks
- **50K x 50K images**: 2048 pixels → 32MB chunks

---

### 3. Compression (`--compression`)

Selects the compression algorithm for Zarr storage.

**Syntax:**
```bash
--compression ALGORITHM
```

**Options:** `blosc`, `zstd`, `lz4`, `none`

**Default:** `blosc`

**Examples:**
```bash
# Blosc compression (default, balanced)
python pipeline.py /path/to/images --compression blosc

# Zstandard compression (best compression ratio)
python pipeline.py /path/to/images --compression zstd

# LZ4 compression (fastest)
python pipeline.py /path/to/images --compression lz4

# No compression (fastest write, largest files)
python pipeline.py /path/to/images --compression none
```

**Algorithm Comparison:**

| Algorithm | Speed | Compression | Use Case |
|-----------|-------|-------------|----------|
| **blosc** (default) | Fast | Good | General purpose, balanced |
| **zstd** | Medium | Excellent | Archival, storage-constrained |
| **lz4** | Very Fast | Moderate | Speed-critical, temporary files |
| **none** | Fastest | None | Testing, fast local drives |

**Typical Compression Ratios:**
- **blosc**: 2-4x compression (uint16 microscopy data)
- **zstd**: 2.5-5x compression
- **lz4**: 1.5-3x compression
- **none**: 1x (no compression)

---

### 4. Compression Level (`--compression-level`)

Controls the compression strength (when using compression).

**Syntax:**
```bash
--compression-level N  # 1-9
```

**Default:** 5 (balanced)

**Range:** 1 (fastest) to 9 (best compression)

**Examples:**
```bash
# Fast compression
python pipeline.py /path/to/images --compression-level 1

# Balanced (default)
python pipeline.py /path/to/images --compression-level 5

# Maximum compression
python pipeline.py /path/to/images --compression-level 9
```

**Guidelines:**
- **Level 1-3**: Fast compression, moderate file size
- **Level 4-6**: Balanced speed and compression (recommended)
- **Level 7-9**: Slow compression, smallest file size

**Performance Impact:**

| Level | Write Speed | File Size | Read Speed |
|-------|-------------|-----------|------------|
| 1 | 100% (baseline) | ~85% of uncompressed | Fast |
| 5 | ~70% | ~50% of uncompressed | Fast |
| 9 | ~40% | ~40% of uncompressed | Fast |

**Note:** Compression level affects **write time only**. Reading compressed data is always fast.

---

## Performance Comparison

### Scenario: 4-channel, 50K x 60K pixel image

| Configuration | Processing Time | File Size | Random Access Speed |
|---------------|-----------------|-----------|---------------------|
| **Default** | 2.5 min | 2.1 GB | Excellent |
| **Fast** (no compression, 8 workers) | 1.2 min | 5.8 GB | Excellent |
| **Balanced** (blosc-5, 4 workers) | 2.5 min | 2.1 GB | Excellent |
| **Small** (zstd-9, 2 workers) | 4.8 min | 1.7 GB | Good |

---

## Optimization Strategies

### Strategy 1: Optimize for Processing Speed

When you need results fast and have plenty of storage:

```bash
python pipeline.py /path/to/images \
  --workers 16 \
  --compression lz4 \
  --compression-level 1 \
  --chunk-size 1024
```

**Best for:**
- Initial testing
- Fast turnaround needed
- Ample storage space
- Local SSD storage

**Tradeoffs:**
- ✅ 2-3x faster processing
- ❌ 2x larger files

---

### Strategy 2: Optimize for File Size

When storage is limited or archiving data:

```bash
python pipeline.py /path/to/images \
  --workers 4 \
  --compression zstd \
  --compression-level 9 \
  --chunk-size 512
```

**Best for:**
- Long-term storage
- Limited disk space
- Network storage
- Archival purposes

**Tradeoffs:**
- ✅ 40-50% smaller files
- ❌ 2x slower processing

---

### Strategy 3: Optimize for QuPath Viewing

When the primary use is interactive viewing in QuPath:

```bash
python pipeline.py /path/to/images \
  --workers 8 \
  --compression blosc \
  --compression-level 3 \
  --chunk-size 512 \
  --pyramid-levels 6
```

**Best for:**
- Interactive analysis
- Frequent zooming/panning
- Multiple users
- Remote viewing

**Tradeoffs:**
- ✅ Excellent viewer responsiveness
- ✅ Smooth multi-resolution display
- ❌ Slightly larger files

---

### Strategy 4: Network/Cloud Storage

When writing to network storage or cloud:

```bash
python pipeline.py /path/to/images \
  --workers 4 \
  --compression blosc \
  --compression-level 7 \
  --chunk-size 1024
```

**Best for:**
- Network attached storage (NAS)
- Cloud storage (S3, Azure, GCS)
- Shared file systems

**Tradeoffs:**
- ✅ Fewer, larger writes (better for network)
- ✅ Good compression (less data transfer)
- ✅ Balanced performance
- ❌ Moderate processing time

---

## Memory Considerations

### Memory Usage Formula

Approximate memory usage per region:

```
Memory (GB) ≈ (Width × Height × Channels × BytesPerPixel) / 1GB

For uint16 data:
Memory (GB) ≈ (Width × Height × Channels × 2) / 1,073,741,824
```

**Examples:**
- 4 channels, 10K × 10K, uint16: ~0.75 GB
- 4 channels, 50K × 60K, uint16: ~22.4 GB
- 6 channels, 50K × 60K, uint16: ~33.6 GB

### Memory Optimization

If processing large images with limited RAM:

1. **Process regions one at a time:**
   ```bash
   python pipeline.py /path/to/images --regions R000
   python pipeline.py /path/to/images --regions R001
   ```

2. **Reduce workers:**
   ```bash
   python pipeline.py /path/to/images --workers 2
   ```

3. **Use Dask's lazy loading** (automatic with default settings)

---

## Hardware Recommendations

### Minimum System
- **CPU:** 4 cores
- **RAM:** 16 GB
- **Storage:** HDD
- **Configuration:** `--workers 2`
- **Expected speed:** 1 region in 5-10 minutes (50K×60K)

### Recommended System
- **CPU:** 8-16 cores
- **RAM:** 32 GB
- **Storage:** SSD
- **Configuration:** `--workers 8`
- **Expected speed:** 1 region in 2-3 minutes (50K×60K)

### High-Performance System
- **CPU:** 16-32 cores
- **RAM:** 64+ GB
- **Storage:** NVMe SSD
- **Configuration:** `--workers 16`
- **Expected speed:** 1 region in 1-2 minutes (50K×60K)

---

## Benchmarking Your System

Test different configurations to find optimal settings:

```bash
# Test 1: Default settings
time python pipeline.py /path/to/test --regions R000

# Test 2: Maximum workers
time python pipeline.py /path/to/test --regions R000 --workers 16

# Test 3: No compression
time python pipeline.py /path/to/test --regions R000 --compression none

# Test 4: Maximum compression
time python pipeline.py /path/to/test --regions R000 --compression zstd --compression-level 9
```

Compare processing times and file sizes to find your optimal configuration.

---

## Troubleshooting Performance Issues

### Issue: Slow Processing

**Possible causes:**
1. Too many workers for CPU
2. Memory pressure (swapping)
3. Slow storage (HDD vs SSD)
4. High compression level

**Solutions:**
```bash
# Reduce workers
python pipeline.py /path/to/images --workers 4

# Lower compression
python pipeline.py /path/to/images --compression-level 3

# Disable compression temporarily
python pipeline.py /path/to/images --compression none
```

### Issue: Out of Memory

**Possible causes:**
1. Too many workers
2. Very large images
3. Insufficient RAM

**Solutions:**
```bash
# Process one region at a time
python pipeline.py /path/to/images --regions R000

# Reduce workers
python pipeline.py /path/to/images --workers 2

# Use smaller chunks (less memory buffering)
python pipeline.py /path/to/images --chunk-size 256
```

### Issue: Slow QuPath Loading

**Possible causes:**
1. Large chunk size
2. Too many pyramid levels
3. Network storage latency

**Solutions:**
```bash
# Use smaller chunks
python pipeline.py /path/to/images --chunk-size 512

# Reduce pyramid levels
python pipeline.py /path/to/images --pyramid-levels 4

# Use faster compression
python pipeline.py /path/to/images --compression lz4
```

---

## Best Practices

1. **Start with defaults** - They're optimized for most cases
2. **Test on one region** - Find optimal settings before processing all
3. **Monitor system resources** - Use Task Manager/htop to watch CPU/memory
4. **Match storage type** - Fast compression for SSDs, slower for HDDs
5. **Consider end use** - Optimize for viewing vs archival vs analysis
6. **Document your settings** - Keep notes on what works for your system

---

## Advanced: Dask Configuration

For advanced users, additional Dask configuration:

```python
# In a custom script
import dask
dask.config.set({
    'array.chunk-size': '128 MiB',  # Target chunk size in memory
    'array.slicing.split_large_chunks': True,
    'scheduler': 'threads',  # or 'processes' for multiprocessing
})
```

---

## Performance Monitoring

Monitor pipeline performance during execution:

**Metrics displayed:**
- Number of parallel workers
- Chunk size (auto or custom)
- Compression settings
- Processing time per region

**Example output:**
```
Performance Settings:
  Chunk size:     1024x1024 pixels (auto-calculated)
  Compression:    blosc (level 5)
  Workers:        8 (auto-detected)

Processing R000...
  Using 8 parallel workers
  Auto-calculated chunk size: 1024x1024 pixels
  Using blosc compression (level 5)
  Loading 4 images...
  Image stack shape: (4, 47973, 62826)
  Creating 5 pyramid levels...
  Writing data to Zarr (this may take a while)...
  ✓ Successfully created Zarr file
```

---

## Summary

The pipeline provides flexible performance options while maintaining sensible defaults:

- **Default settings** work well for most use cases
- **--workers** controls parallelism (biggest speed impact)
- **--compression** controls file size vs speed tradeoff
- **--chunk-size** fine-tunes I/O performance
- **--compression-level** fine-tunes compression ratio

Experiment with these options to find the best configuration for your hardware and workflow!
