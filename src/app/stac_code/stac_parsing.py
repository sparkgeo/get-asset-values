"""
Provides functions for parsing STAC (SpatioTemporal Asset Catalog) items,
retrieving specific assets such as COG (Cloud Optimized GeoTIFF) URLs.
"""

import json
import os
from pathlib import Path

import requests

from app.get_values_logger import logger


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
    try:
        token = os.environ.get("STAC_API_KEY")
        headers = {"Authorization": f"Bearer {token}"}
        logger.debug(f"Attempting to open URL: {url}")
        with requests.get(url, headers=headers) as f:
            try:
                logger.debug(f"Successfully opened URL: {url}")
                stac_item = f.json()
            except json.JSONDecodeError as e:
                logger.error(f"Error loading JSON from {url}: {type(e).__name__}: {e}")
                raise ValueError(
                    f"Error loading JSON from {url}: {type(e).__name__}: {e}"
                ) from e
    except Exception as e:
        logger.error(f"Error opening {url}: {type(e).__name__}: {e}")
        raise ValueError(f"Error opening {url}: {type(e).__name__}: {e}") from e
    return stac_item


def get_asset_details_from_stac_url(stac_url: str) -> dict:
    """
    Retrieve asset details from a
    STAC (SpatioTemporal Asset Catalog) URL.

    Args:
        stac_url (str): The URL of the STAC item.

    Returns:
        dict: A dictionary containing the COG details extracted from the STAC item.
    """
    stac_item = get_stac_item(stac_url)
    asset_details = get_asset_details(stac_item)
    return asset_details


def get_asset_details(stac_item: dict) -> dict:
    """
    Extract the URL of the first asset
    found in the STAC item's assets.

    Iterates through the assets in the provided STAC item, looking
    for an asset with a media type of 'image/tiff' and returns the
    URL of the first match along with the datetime property of the STAC item.

    Parameters:
    - stac_item (dict): The STAC item to search through.

    Returns:
     - dict: A dictionary containing the URL of the COG asset and the datetime property,
            if found. None otherwise.
    """
    file_types = [".tif", ".tiff", ".json"]
    logger.debug(f"STAC item: {stac_item}")
    logger.info("Getting asset details")
    for _, asset_value in stac_item.get("assets", {}).items():
        asset_url = asset_value.get("href")
        asset_suffix = Path(asset_url).suffix
        logger.info(f"Asset path: {asset_suffix}")
        if asset_suffix in file_types:
            asset_url = asset_value.get("href")
            dt = stac_item.get("properties", {}).get("datetime")
            source_file_name = Path(asset_url).stem.replace(".", "-")
            unit = stac_item.get("properties", {}).get("unit")
            return {
                "url": asset_url,
                "datetime": dt,
                "source_file_name": source_file_name,
                "unit": unit,
            }
    return None


def get_asset_data(stac_item_url_list: list[str]) -> list[dict]:
    """
    Retrieve a list of asset URLs from a list of STAC item URLs.

    This function retrieves a list of assets
    URLs from a list of STAC (SpatioTemporal Asset Catalog) item
    URLs. It uses the `get_stac_item` and `get_asset_url` functions
    to load and extract the URLs.

    Parameters:
    - stac_item_url_list (list[dict]): A list of URLs of STAC items.

    Returns:
    - list[str]: A list of assets found in the STAC items.
    """
    asset_urls = []
    for stac_item_url in stac_item_url_list:
        stac_item = get_stac_item(stac_item_url)
        asset_url = get_asset_details(stac_item)
        asset_urls.append(asset_url)
    return asset_urls
