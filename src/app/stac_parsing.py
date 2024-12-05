"""
Provides functions for parsing STAC (SpatioTemporal Asset Catalog) items,
retrieving specific assets such as COG (Cloud Optimized GeoTIFF) URLs.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

from app.get_values_logger import logger


@dataclass
class AssetDetails:
    url: str
    datetime: datetime
    source_file_name: str
    unit: str

    def to_dict(self):
        return {
            "url": self.url,
            "datetime": self.datetime,
            "source_file_name": self.source_file_name,
            "unit": self.unit,
        }


class StacItem:
    def __init__(self, url: str):
        self.url = url
        self.stac_item = self.get_stac_item()
        self.asset_details = self.get_asset_details()

    def get_stac_item(self) -> dict:
        """
        Retrieve a STAC item from a specified URL.

        This function opens a given URL to read a STAC (SpatioTemporal
        Asset Catalog) item, assuming the resource is publicly
        accessible without authentication.

        Parameters:

        Returns:
        - dict: The STAC item loaded as a dictionary.
        """
        try:
            logger.debug(f"Attempting to open URL: {self.url}")
            response = requests.get(self.url)
            response.raise_for_status()
            stac_item = response.json()
            return stac_item
        except (requests.RequestException, json.JSONDecodeError) as e:
            if isinstance(e, requests.RequestException):
                logger.error(f"Error opening {self.url}: {type(e).__name__}: {e}")
                raise ValueError(
                    f"Error opening {self.url}: {type(e).__name__}: {e}"
                ) from e
            elif isinstance(e, json.JSONDecodeError):
                logger.error(
                    f"Error loading JSON from {self.url}: {type(e).__name__}: {e}"
                )
                raise ValueError(
                    f"Error loading JSON from {self.url}: {type(e).__name__}: {e}"
                ) from e

    def get_asset_details(self) -> AssetDetails:
        """
        Extract the URL of the first asset
        found in the STAC item's assets.

        Iterates through the assets in the provided STAC item, looking
        for an asset with a media type of 'image/tiff' and returns the
        URL of the first match along with the datetime property of the STAC item.

        Parameters:

        Returns:
        - dict: A dictionary containing the properties of the assets, if found.
        None otherwise.
        """
        file_types = [".tif", ".tiff", ".json"]
        logger.debug("Getting asset details")
        for _, asset_value in self.stac_item.get("assets", {}).items():
            url = asset_value.get("href")
            asset_suffix = Path(url).suffix
            if asset_suffix in file_types:
                dt = self.stac_item.get("properties", {}).get("datetime")
                source_file_name = Path(url).stem.replace(".", "-")
                unit = self.stac_item.get("properties", {}).get("unit")
                return AssetDetails(url, dt, source_file_name, unit)


def get_asset_data_list(stac_item_url_list: list[str]) -> list[AssetDetails]:
    """
    Retrieve a list of asset details from a list of STAC item URLs.

    This function retrieves a list of assetsdetails
    from a list of STAC (SpatioTemporal Asset Catalog) item
    URLs.

    Parameters:
    - stac_item_url_list (list[dict]): A list of URLs of STAC items.

    Returns:
    - list[AssetDetails]: A list of asset details found in the STAC items.
    """
    asset_details_list = []
    for stac_item_url in stac_item_url_list:
        asset_details = StacItem(stac_item_url).asset_details
        asset_details_list.append(asset_details)
    return asset_details_list
