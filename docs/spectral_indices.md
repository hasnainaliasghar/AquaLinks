# Spectral indices

AquaLens computes six normalised band-math indices over the water mask
of a Sentinel-2 L2A scene. The formulas follow the standard
remote-sensing definitions; for each index the implementation lives in
[`backend/app/services/indices.py`](../backend/app/services/indices.py).

## Bands used

| Friendly name | Sentinel-2 band | Wavelength |
| --- | --- | --- |
| Blue | B02 | ~492 nm |
| Green | B03 | ~559 nm |
| Red | B04 | ~665 nm |
| Red Edge | B05 | ~704 nm |
| NIR | B08 | ~833 nm |
| SWIR | B11 | ~1610 nm |

All bands are read as surface-reflectance values scaled to `[0, 1]`
(Sentinel-2 L2A divides by 10 000). Bands with different native
resolutions are nearest-neighbour resampled to the 10 m grid before
math.

## Indices

### NDWI — Normalised Difference Water Index

```
NDWI = (NIR - SWIR) / (NIR + SWIR)
```

Positive values typically indicate open water. AquaLens uses
`NDWI > 0` as the water mask for aggregation.

### MNDWI — Modified NDWI

```
MNDWI = (Green - SWIR) / (Green + SWIR)
```

Replaces NIR with green to reduce confusion between water and built-up
surfaces. Useful in urban catchments.

### NDTI — Normalised Difference Turbidity Index

```
NDTI = (Red - Green) / (Red + Green)
```

Higher values indicate increased turbidity (more red reflectance from
suspended sediment).

### NDCI — Normalised Difference Chlorophyll Index

```
NDCI = (RedEdge - Red) / (RedEdge + Red)
```

A proxy for chlorophyll-a using the red-edge band. Elevated values are
a precursor for harmful algal blooms but not a direct toxin measurement.

### NDVI — Normalised Difference Vegetation Index

```
NDVI = (NIR - Red) / (NIR + Red)
```

Targets vegetation but is included to flag floating biomass and
shoreline stress that often co-occur with water-quality issues.

### WRI — Water Ratio Index

```
WRI = (Green + Red) / (NIR + SWIR)
```

Values ≥ 1 indicate moisture; values above 2.5 typically indicate clear
open water.

## Aggregation

Each index is aggregated to the masked-mean over the water polygon:

1. Apply the AOI mask returned by `rasterio.mask`.
2. Drop NaNs and non-water pixels (`NDWI ≤ 0`).
3. Compute `mean`, `min`, `max`, `stddev`, and `sample_count`.

The aggregate plus an interpretation string (`"high turbidity"` etc.)
is what lands in the `spectral_indices` table.

## Citations

- *Types of water indices and their applications* — Innoter, used for
  NDWI, MNDWI, NDTI, and WRI definitions.
- *Sentinel-2 NDCI* — Lens by Upstream Tech.
- *NDVI* — NASA Earthdata.
