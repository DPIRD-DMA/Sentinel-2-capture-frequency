from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Union

import geopandas as gpd
import numpy as np
from geopandas import GeoSeries
from pystac.item import Item
from shapely.geometry import Polygon
from tqdm.auto import tqdm

from helpers.network import download_index, get_scenes
from helpers.raster import export_raster, rasterize_scenes


def get_coverage(scenes: List[Item]) -> gpd.GeoDataFrame:
    extents = []
    for scene in scenes:
        if scene.geometry is not None and "coordinates" in scene.geometry:
            extents.append(Polygon(scene.geometry["coordinates"][0]))

    extent_gdf = gpd.GeoDataFrame(geometry=extents, crs="EPSG:4326")  # type: ignore
    return extent_gdf


def process_scene(
    row: GeoSeries,
    min_year: int,
    max_year: int,
    global_raster: np.ndarray,
    resolution: float,
    x_min: float,
    y_max: float,
) -> Optional[np.ndarray]:
    scenes = get_scenes(row, min_year, max_year)
    if not scenes:
        return None
    extents = get_coverage(scenes)
    return rasterize_scenes(extents, global_raster, resolution, x_min, y_max)


def build_revisit_raster(
    export_path: Union[Path, str] = Path.cwd() / "Output.tif",
    resolution: float = 0.00278,
    min_year: int = 2023,
    max_year: int = 2023,
    count_limit: Optional[int] = None,
    debug_mode: bool = False,
) -> None:
    """
    Downloads the Sentinel-2 index, calculates the extent of a global raster based
    on specified parameters, and exports the resulting raster to a given path.

    This function generates a global raster by processing Sentinel-2 scenes within
    a specified time frame and geographical extent. It uses a ThreadPoolExecutor to
    parallelize the processing of individual scenes.

    Args:
        export_path (Path): The file path where the output raster is to be saved.
                            Defaults to the current working directory with the filename 'Output.tif'.
        resolution (float): The spatial resolution of the output raster in degrees. Defaults to 0.00278.
        min_year (int): The starting year for Sentinel-2 scene selection. Defaults to 2023.
        max_year (int): The ending year for Sentinel-2 scene selection. Defaults to 2023.
        x_min (float): The minimum longitude of the raster extent. Defaults to -180.0.
        y_min (float): The minimum latitude of the raster extent. Defaults to -90.0.
        x_max (float): The maximum longitude of the raster extent. Defaults to 180.0.
        y_max (float): The maximum latitude of the raster extent. Defaults to 90.0.

    Returns:
        None: The function does not return a value but exports the generated raster to the specified path.
    """
    s2_index_path = download_index()
    s2_index_gdf = gpd.read_file(s2_index_path)
    bounds = s2_index_gdf.total_bounds
    bounds_buffer = 1.2
    x_min, y_min, x_max, y_max = (
        bounds[0] * bounds_buffer,
        bounds[1] * bounds_buffer,
        bounds[2] * bounds_buffer,
        bounds[3] * bounds_buffer,
    )
    if count_limit is not None:
        s2_index_gdf = s2_index_gdf.head(count_limit)

    width = int((x_max - x_min) / resolution)
    height = int((y_max - y_min) / resolution)
    global_raster = np.zeros((height, width), dtype=np.uint16)

    if debug_mode:
        for _, row in tqdm(s2_index_gdf.iterrows(), total=len(s2_index_gdf)):
            result = process_scene(
                row, min_year, max_year, global_raster, resolution, x_min, y_max
            )
            if result is not None:
                global_raster = result
    else:
        # Create a ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            # Submit tasks to the executor
            for _, row in s2_index_gdf.iterrows():
                futures.append(
                    executor.submit(
                        process_scene,
                        row,
                        min_year,
                        max_year,
                        global_raster,
                        resolution,
                        x_min,
                        y_max,
                    )
                )

            for future in tqdm(as_completed(futures), total=len(futures)):
                try:
                    result = future.result()
                    if result is not None:
                        global_raster = result
                except Exception as exc:
                    print(f"Row {row} generated an exception: {exc}")  # type: ignore

    export_raster(
        global_raster, x_min, y_min, x_max, y_max, width, height, Path(export_path)
    )
