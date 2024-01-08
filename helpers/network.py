from pathlib import Path
from typing import List

import pystac_client
import requests
import shapely
from geopandas import GeoSeries
from pystac.item import Item


def get_scenes(
    row: GeoSeries, extract_start_year: int, extract_end_year: int, retry: int = 3
) -> List[Item]:
    bounds = row.geometry.buffer(-0.1)

    query = {
        "collections": ["sentinel-2-l2a"],
        "intersects": shapely.to_geojson(bounds),
        "datetime": f"{extract_start_year}-01-01T00:00:00Z/{extract_end_year}-12-31T23:59:59Z",
        "query": {"s2:mgrs_tile": {"eq": row.Name}},
    }
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
    )
    try:
        item_collection = catalog.search(**query).item_collection()
        items = list(item_collection)
    except:
        if retry > 0:
            return get_scenes(row, extract_start_year, extract_end_year, retry - 1)
        else:
            return []

    return items


urls = [
    "https://raw.githubusercontent.com/justinelliotmeyers/Sentinel-2-Shapefile-Index/master/sentinel_2_index_shapefile.cpg",
    "https://raw.githubusercontent.com/justinelliotmeyers/Sentinel-2-Shapefile-Index/master/sentinel_2_index_shapefile.dbf",
    "https://raw.githubusercontent.com/justinelliotmeyers/Sentinel-2-Shapefile-Index/master/sentinel_2_index_shapefile.prj",
    "https://raw.githubusercontent.com/justinelliotmeyers/Sentinel-2-Shapefile-Index/master/sentinel_2_index_shapefile.sbn",
    "https://raw.githubusercontent.com/justinelliotmeyers/Sentinel-2-Shapefile-Index/master/sentinel_2_index_shapefile.sbx",
    "https://raw.githubusercontent.com/justinelliotmeyers/Sentinel-2-Shapefile-Index/master/sentinel_2_index_shapefile.shp",
    "https://raw.githubusercontent.com/justinelliotmeyers/Sentinel-2-Shapefile-Index/master/sentinel_2_index_shapefile.shx",
]


def download_file(url: str) -> Path:
    """Download a file from a given URL.

    Args:
        url (str): The URL of the file to be downloaded.

    Returns:
        Path: The path to the downloaded file.
    """
    local_filename = url.split("/")[-1]
    download_folder = Path.cwd() / "S2 index"
    download_folder.mkdir(exist_ok=True)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        dl_path = download_folder / local_filename
        if dl_path.exists():
            return dl_path
        with open(dl_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return dl_path


def download_index() -> Path:
    """Download Sentinel-2 shapefiles and return the path of the .shp file.

    Returns:
        Path: The path to the downloaded .shp file.
    """
    downloaded_files = [download_file(url) for url in urls]
    return downloaded_files[5]
