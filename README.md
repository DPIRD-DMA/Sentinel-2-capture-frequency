# Sentinel-2-capture-frequency

## Overview
This tool, developed in Python, analyzes the frequency of Sentinel-2 satellite scene coverages. It integrates the extent polygons from the Microsoft Planetary Computer to produce a global raster. Each pixel in this raster reflects the number of observations of that location in Sentinel-2 scenes.

## Features
- Accessing and utilizing Sentinel-2 index data from Microsoft Planetary Computer.
- Combining and rasterizing satellite scene coverage polygons.
- Generating a global raster map to visualize satellite coverage.

## Installation
Ensure Python is installed on your system and then install the necessary dependencies.

### Dependencies
- geopandas
- rasterio
- pystac
- tqdm

Install these packages via pip:
```bash
pip install geopandas rasterio pystac tqdm
git clone https://github.com/DPIRD-DMA/Sentinel-2-capture-frequency
```

## Usage
Follow these steps to use the tool:

1. **Define Parameters**: Set the geographical bounds and the time frame for your analysis.
2. **Data Processing**: The tool processes the Sentinel-2 index data, combining scene extents into a global raster map.
3. **Export Results**: Outputs are saved as a GeoTIFF file, showing the satellite coverage areas.

Example:
```python
from pathlib import Path
from helpers.coordinator import get_s2_revisit_frequency

process_scene_coverage(
    export_path=Path('/path/to/output.tif'),
    resolution=0.00278,
    min_year=2023,
    max_year=2023,
    x_min=-180.0,
    y_min=-90.0,
    x_max=180.0,
    y_max=90.0
)
```

## License
[MIT License](LICENSE)