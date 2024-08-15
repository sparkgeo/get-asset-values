"""
Provides functions for parsing STAC (SpatioTemporal Asset Catalog) items,
retrieving specific assets such as COG (Cloud Optimized GeoTIFF) URLs.
"""

import json
from datetime import datetime

import fsspec


def get_stac_item(url: str) -> dict:
    """
    Retrieve a STAC item from a specified URL.

    This function opens a given URL to read a STAC (SpatioTemporal
    Asset Catalog) item, assuming the resource is publicly
    accessible without authentication.

    Parameters:
    - url (str): The URL of the STAC item to retrieve.

    Returns:
    - dict: The STAC item loaded as a dictionary.
    """
    with fsspec.open(url, anon=True) as f:
        stac_item = json.load(f)
    return stac_item


def get_cog_url(stac_item: dict) -> str:
    """
    Extract the URL of the first COG (Cloud Optimized GeoTIFF)
    found in the STAC item's assets.

    Iterates through the assets in the provided STAC item, looking
    for an asset with a media type of 'image/tiff' and returns the
    URL of the first match.

    Parameters:
    - stac_item (dict): The STAC item to search through.

    Returns:
    - str: The URL of the COG asset, if found. None otherwise.
    """
    # TODO: Get this to work with multiple assets including zarr files
    for asset in stac_item["assets"]:
        output_name = f"{stac_item['properties']['eo:bands'][0]['common_name']}_{datetime.fromisoformat(stac_item['properties']['datetime']).date()}"
        media_type = stac_item["assets"][asset]["type"]
        if "image/tiff" in media_type:
            return {
                output_name: output_name,
                "asset_href": stac_item["assets"][asset]["href"],
            }


def get_cog_urls(stac_item_url_list: list[str]) -> list[str]:
    """
    Retrieve a list of COG URLs from a list of STAC item URLs.

    This function retrieves a list of COG (Cloud Optimized GeoTIFF)
    URLs from a list of STAC (SpatioTemporal Asset Catalog) item
    URLs. It uses the `get_stac_item` and `get_cog_url` functions
    to load and extract the URLs.

    Parameters:
    - stac_item_url_list (list[str]): A list of URLs of STAC items.

    Returns:
    - list[str]: A list of URLs of COG assets found in the STAC items.
    """
    cog_urls = []
    for stac_item_url in stac_item_url_list:
        stac_item = get_stac_item(stac_item_url)
        cog_url = get_cog_url(stac_item)
        cog_urls.append(cog_url)
    return cog_urls
