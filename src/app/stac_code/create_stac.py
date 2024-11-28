import datetime as dt
import mimetypes
import os
import time
from pathlib import Path

out_dir = os.getcwd()


def createStacItem(outName: str) -> dict:
    """
    Create a STAC (SpatioTemporal Asset Catalog) item from the given output file name.

    Args:
        outName (str): The name of the output file
        for which the STAC item is to be created.

    Returns:
        data (dict): The STAC item data.
    """
    stem = Path(outName).stem
    now = time.time_ns() / 1_000_000_000
    dateNow = dt.datetime.fromtimestamp(now)
    dateNow = dateNow.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    size = os.path.getsize(f"{outName}")
    mime = mimetypes.guess_type(f"{outName}")[0]
    data = {
        "stac_version": "1.0.0",
        "id": f"{stem}-{now}",
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[-180, -90], [-180, 90], [180, 90], [180, -90], [-180, -90]]
            ],
        },
        "properties": {
            "created": f"{dateNow}",
            "datetime": f"{dateNow}",
            "updated": f"{dateNow}",
        },
        "bbox": [-180, -90, 180, 90],
        "assets": {
            f"{stem}": {
                "type": f"{mime}",
                "roles": ["data"],
                "href": f"{outName}",
                "file:size": size,
            }
        },
        "links": [
            {"type": "application/json", "rel": "parent", "href": "catalog.json"},
            {"type": "application/geo+json", "rel": "self", "href": f"{stem}.json"},
            {"type": "application/json", "rel": "root", "href": "catalog.json"},
        ],
    }
    return data


def createStacCatalogRoot(outName: str) -> dict:
    """
    Create the root STAC (SpatioTemporal Asset Catalog) catalog
    from the given output file name.

    Args:
        outName (str): The name of the output file for which the root STAC
        catalog is to be created.

    Returns:
        data (dict): The root STAC catalog data.
    """
    stem = Path(outName).stem
    data = {
        "stac_version": "1.0.0",
        "id": "catalog",
        "type": "Catalog",
        "description": "Root catalog",
        "links": [
            {"type": "application/geo+json", "rel": "item", "href": f"{stem}.json"},
            {"type": "application/json", "rel": "self", "href": "catalog.json"},
        ],
    }
    return data
