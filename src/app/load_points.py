"""
Functions to load points into a dataset
"""

import json

import numpy as np
import xarray as xr

from app.get_values_logger import logger


def load_json(json_file: str) -> dict:
    """
    Loads points data from a JSON file.

    Parameters:
    - json_file (str): Path to the JSON file.

    Returns:
    dict: Points data loaded from the file.
    """
    logger.info("Loading json file from %s", json_file)
    try:
        with open(json_file, encoding="utf-8") as f:
            points_data = json.load(f)
        return points_data
    except json.JSONDecodeError as e:
        logger.error("Error loading JSON file(%s): %s", json_file, e)
        raise


def points_to_xr_dataset(points_data: dict) -> xr.Dataset:
    """
    Converts points data to an xarray Dataset.

    Parameters:
    - points_data (dict): Data containing points in GeoJSON format.

    Returns:
    xr.Dataset: Dataset with points as coordinates.

    Raises:
    ValueError: If the input data is missing or invalid.
    """
    logger.info("Converting points to xarray Dataset")
    try:
        features = points_data["features"]
        latitudes = np.array(
            [feature["geometry"]["coordinates"][1] for feature in features]
        )
        longitudes = np.array(
            [feature["geometry"]["coordinates"][0] for feature in features]
        )
    except (KeyError, TypeError, IndexError) as e:
        logger.error(f"Invalid points data: {e}")
        raise ValueError("Invalid points data") from e

    dataset = xr.Dataset(
        {"x": (["points"], longitudes), "y": (["points"], latitudes)},
    )
    return dataset


def load_json_to_xr_dataset(json_file: str) -> xr.Dataset:
    """
    Loads JSON to xarray Dataset with specified keys.

    Parameters:
    - json_file (str): Path to the JSON file.

    Returns:
    xr.Dataset: Dataset with points as coordinates.
    """
    points_data = load_json(json_file)
    return points_to_xr_dataset(points_data)
