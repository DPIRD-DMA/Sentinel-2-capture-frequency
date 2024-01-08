from pathlib import Path
from typing import Tuple

import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio.features import rasterize


def get_index(
    bbox: Tuple[float, float, float, float], minx: float, miny: float, resolution: float
) -> Tuple[int, int, int, int]:
    """
    Calculate row and column start and end indices from a bounding box.

    Args:
        bbox (Tuple[float, float, float, float]): The bounding box as a tuple (minx, miny, maxx, maxy).
        minx (float): Minimum x-value of the bounding box.
        miny (float): Maximum y-value of the bounding box.
        resolution (float): Resolution of the raster.

    Returns:
        Tuple[int, int, int, int]: Tuple of (row_start, row_end, col_start, col_end) indices.
    """
    col_start = int((bbox[0] - minx) / resolution)
    row_start = int((miny - bbox[3]) / resolution)
    col_end = int((bbox[2] - minx) / resolution)
    row_end = int((miny - bbox[1]) / resolution)
    return row_start, row_end, col_start, col_end


def rasterize_scenes(
    gdf: gpd.GeoDataFrame,
    global_raster: np.ndarray,
    resolution: float,
    x_min: float,
    y_max: float,
) -> np.ndarray:
    """
    Rasterizes polygons in a GeoDataFrame onto a global raster array.

    Args:
        gdf (gpd.GeoDataFrame): GeoDataFrame containing polygons to rasterize.
        global_raster (np.ndarray): The global raster array to rasterize onto.
        resolution (float): The resolution of the raster.
        x_min (float): The minimum x-coordinate of the global raster.
        y_max (float): The maximum y-coordinate of the global raster.

    Returns:
        np.ndarray: The updated global raster array with the rasterized polygons.
    """

    # Rasterize each polygon
    for polygon in gdf.geometry:
        bbox = polygon.bounds
        bbox_width = int((bbox[2] - bbox[0]) / resolution)
        bbox_height = int((bbox[3] - bbox[1]) / resolution)
        transform = rio.transform.from_origin(bbox[0], bbox[3], resolution, resolution)  # type: ignore

        # Rasterize the polygon within its bounding box
        rasterized = rasterize(
            [(polygon, 1)], out_shape=(bbox_height, bbox_width), transform=transform
        )

        # Get indices in the global raster
        row_start, row_end, col_start, col_end = get_index(
            bbox, x_min, y_max, resolution
        )

        # Ensure the dimensions match exactly for the global slice
        global_slice = global_raster[
            row_start : row_start + (row_end - row_start),
            col_start : col_start + (col_end - col_start),
        ]

        # Adjust the dimensions of the rasterized array to match the global raster
        rasterized_adjusted = np.zeros(global_slice.shape).astype("uint16")
        min_height, min_width = min(
            rasterized_adjusted.shape[0], rasterized.shape[0]
        ), min(rasterized_adjusted.shape[1], rasterized.shape[1])
        rasterized_adjusted[:min_height, :min_width] = rasterized[
            :min_height, :min_width
        ]

        # Add the adjusted rasterized array to the global slice
        global_raster[
            row_start : row_start + rasterized_adjusted.shape[0],
            col_start : col_start + rasterized_adjusted.shape[1],
        ] += rasterized_adjusted

    return global_raster


def export_raster(
    global_raster: np.ndarray,
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
    width: int,
    height: int,
    export_path: Path,
):
    """Export a raster dataset to a GeoTIFF file.

    This function saves a NumPy array as a geospatial raster in GeoTIFF format,
    using the rasterio library. It requires the bounds of the raster in geographical
    coordinates and the dimensions of the output file.

    Args:
        global_raster (np.ndarray): The raster data as a NumPy array.
        x_min (float): Minimum x-coordinate (longitude) of the raster bounds.
        y_min (float): Minimum y-coordinate (latitude) of the raster bounds.
        x_max (float): Maximum x-coordinate (longitude) of the raster bounds.
        y_max (float): Maximum y-coordinate (latitude) of the raster bounds.
        width (int): Width of the output raster in pixels.
        height (int): Height of the output raster in pixels.
        export_path (Path): Path object representing the file path to which
                            the raster will be exported.

    """
    with rio.open(
        export_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        nodata=0,
        dtype=global_raster.dtype,
        crs="+proj=latlong",
        compress="lzw",
        transform=rio.transform.from_bounds(x_min, y_min, x_max, y_max, width, height),  # type: ignore
    ) as dst:
        dst.write(global_raster, 1)
