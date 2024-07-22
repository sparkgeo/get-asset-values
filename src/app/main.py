#!/usr/bin/env python3
"""
Main starting point for the Lambda function.
"""

import argparse
import json
import os

from get_values import get_values_from_multiple_cogs, merge_results_into_dict
from get_values_logger import logger
from load_points import check_json, points_to_xr_dataset
from stac_parsing import get_cog_urls

from src.app.load_images import load_multiple_cogs


def get_data_values(
    stac_items: list[str], points_json: dict, latitude_key: str, longitude_key: str
):
    """
    Fetches data values for given points from STAC items.

    This function retrieves Cloud Optimized GeoTIFF (COG) URLs
    from the provided STAC items, loads the COGs, and extracts
    data values at specified points. The results are merged into
    a dictionary structure and returned.

    Parameters:
    - stac_items (list[str]): List of STAC item URLs.
    - points_json (dict): JSON object containing points.
    - latitude_key (str): Key for latitude in points_json.
    - longitude_key (str): Key for longitude in points_json.

    Returns:
    dict: A dictionary with the merged results of data values
    for the provided points.
    """
    cog_item_urls = get_cog_urls(stac_items)
    cog_dss = load_multiple_cogs(cog_item_urls)
    check_json(points_json, latitude_key, longitude_key)
    points = points_to_xr_dataset(points_json, latitude_key, longitude_key)
    return_values = get_values_from_multiple_cogs(datasets=cog_dss, points=points)
    return_json = merge_results_into_dict(return_values, points_json)
    return return_json


def lambda_handler(event, _):
    """
    Handles incoming requests to the Lambda function.

    This function processes events by extracting necessary
    parameters from the event body, validates them, and then
    calls `get_data_values` to fetch data values for given
    points from STAC items.

    Parameters:
    - event (dict): The event dict containing the request body.
    - context: The context in which the Lambda function is called.

    Returns:
    dict: A dictionary with either the fetched data values or
    an error message and corresponding HTTP status code.
    """
    logger.info("Received event: %s", json.dumps(event))
    logger.info("Starting lambda function")
    body = json.loads(event["body"])
    stac_items = body.get("stac_items")
    points_json = body.get("points_json")
    if points_json:
        points_json = json.loads(points_json)
    latitude_key = body.get("latitude_key")
    longitude_key = body.get("longitude_key")
    return process_request(points_json, stac_items, latitude_key, longitude_key)


def process_request(
    points_json: dict,
    stac_items: list[str],
    latitude_key: str,
    longitude_key: str,
    workflow: bool = False,
) -> dict:
    """
    Processes a request to get data values for points.

    Parameters:
    - points_json (dict): JSON containing points data.
    - stac_items (list[str]): List of STAC item IDs.
    - latitude_key (str): Key for latitude in points_json.
    - longitude_key (str): Key for longitude in points_json.

    Returns:
    dict: Response with status code and body.
    """
    if not all([points_json, stac_items, latitude_key, longitude_key]):
        return {"statusCode": 400, "body": json.dumps("Missing required parameters")}
    try:
        response = get_data_values(stac_items, points_json, latitude_key, longitude_key)
        if workflow:
            return response
        else:
            return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as e:
        logger.error("Error: %s", e)
        return {"statusCode": 500, "body": json.dumps(str(e))}


def parse_arguments():
    """
    Parses command-line arguments for the request.

    Returns:
        argparse.Namespace: An object that holds the parsed arguments as
        attributes.
    """
    logger.info("Parsing command-line arguments")
    parser = argparse.ArgumentParser(description="Make a request.")
    # parser.add_argument("--json", type=str, help="JSON string with request parameters")
    parser.add_argument("--points_json", type=str, help="JSON string with points data")
    parser.add_argument("--stac_items", type=str, help="STAC item URLs")
    parser.add_argument(
        "--latitude_key",
        type=str,
        default="latitude",
        help="Key for latitude in points JSON",
    )
    parser.add_argument(
        "--longitude_key",
        type=str,
        default="longitude",
        help="Key for longitude in points JSON",
    )
    return parser.parse_args()


def get_catalog() -> dict:
    """
    Creates and returns a basic STAC catalog dictionary.

    This function generates a dictionary representing a SpatioTemporal Asset Catalog
    (STAC) catalog with predefined properties.

    Returns:
    - dict: A dictionary representing the STAC catalog with predefined properties.
    """
    logger.info("Creating STAC catalog")
    return {
        "stac_version": "1.0.0",
        "id": "asset-vulnerability-catalog",
        "type": "Catalog",
        "description": "OS-C physrisk asset vulnerability catalog",
        "links": [
            {"rel": "self", "href": "./catalog.json"},
            {"rel": "root", "href": "./catalog.json"},
        ],
    }


if __name__ == "__main__":
    args = parse_arguments()
    arg_points_json = json.loads(args.points_json)
    arg_stac_items = json.loads(args.stac_items)
    arg_latitude_key = args.latitude_key
    arg_longitude_key = args.longitude_key
    process_response = process_request(
        points_json=arg_points_json,
        stac_items=arg_stac_items,
        latitude_key=arg_latitude_key,
        longitude_key=arg_longitude_key,
        workflow=True,
    )
    # Make a stac catalog.json file to satitsfy the process runner
    os.makedirs("asset_output", exist_ok=True)
    with open("./asset_output/catalog.json", "w", encoding="utf-8") as f:
        catalog = get_catalog()
        catalog["data"] = process_response
        json.dump(catalog, f)
