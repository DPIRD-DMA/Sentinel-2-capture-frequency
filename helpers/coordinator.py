from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Union, Tuple

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
    row: Tuple[int, GeoSeries],
    min_year: int,
    max_year: int,
    retries: int = 3,
):
    try:
        scenes = get_scenes(row[1], min_year, max_year)
        if not scenes:
            return None
        extents = get_coverage(scenes)
        return extents

    except Exception as e:
        if retries > 0:
            return process_scene(row, min_year, max_year, retries - 1)
        else:
            print(e)
            return None


def build_revisit_raster(
    export_path: Union[Path, str] = Path.cwd() / "Output.tif",
    resolution: float = 0.00278,
    min_year: int = 2023,
    max_year: int = 2023,
    count_limit: Optional[int] = None,
    debug_mode: bool = False,
    scenes_path: Optional[Union[Path, str]] = None,
) -> Path:
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


    Returns:
        None: The function does not return a value but exports the generated raster to the specified path.
    """
    if scenes_path:
        s2_index_path = scenes_path
    else:
        s2_index_path = download_index()
    s2_index_gdf = gpd.read_file(s2_index_path)

    if count_limit is not None:
        s2_index_gdf = s2_index_gdf.head(count_limit)
    if debug_mode:
        result = []
        for row in tqdm(
            s2_index_gdf.iterrows(), total=len(s2_index_gdf), desc="Querying scenes"
        ):
            result.append(process_scene(row, min_year=min_year, max_year=max_year))  # type: ignore
    else:
        with ThreadPoolExecutor() as executor:
            result = list(
                tqdm(
                    executor.map(
                        process_scene,
                        s2_index_gdf.iterrows(),
                        [min_year] * len(s2_index_gdf),
                        [max_year] * len(s2_index_gdf),
                    ),
                    total=len(s2_index_gdf),
                    desc="Querying scenes",
                )
            )

    x_min, y_min = float("inf"), float("inf")
    x_max, y_max = float("-inf"), float("-inf")

    for gdf in result:
        if gdf is not None:
            extent = gdf.total_bounds
            x_min = min(x_min, extent[0])
            y_min = min(y_min, extent[1])
            x_max = max(x_max, extent[2])
            y_max = max(y_max, extent[3])

    width = int((x_max - x_min) / resolution)
    height = int((y_max - y_min) / resolution)
    global_raster = np.zeros((height, width), dtype=np.uint16)

    for gdf in tqdm(result, desc="Rasterizing scenes"):
        if gdf is not None:
            global_raster = rasterize_scenes(
                gdf, global_raster, resolution, x_min, y_max
            )

    export_raster(
        global_raster, x_min, y_min, x_max, y_max, width, height, Path(export_path)
    )
    return Path(export_path)
