#!/usr/bin/env python3
"""
Main starting point for the workflow.
"""

import argparse
import ast
import json
import os
import sys
import tempfile
import traceback

import boto3
import pandas as pd
import requests

from app.get_values import get_values_from_multiple_stac_items, merge_results_into_dict
from app.get_values_logger import logger
from app.load_points import points_to_xr_dataset
from app.stac_code.create_stac import (
    createStacCatalogRoot,
    createStacItem,
)
from app.stac_code.search_stac import (
    process_stac_query_args,
    search_stac,
)


def get_data_values(
    stac_items: list[str], points_json: dict, ds_args: str = None
) -> dict:
    """
    Fetches data values for given points from STAC items.

    This function retrieves Cloud Optimized GeoTIFF (COG) URLs
    from the provided STAC items, loads the COGs, and extracts
    data values at specified points. The results are merged into
    a dictionary structure and returned.

    Parameters:
    - stac_items (list[str]): List of STAC item URLs.
    - points_json (dict): JSON object containing points.

    Returns:
    dict: A dictionary with the merged results of data values
    for the provided points.
    """
    logger.info("Converting points to an xr dataset")
    points = points_to_xr_dataset(points_json)
    logger.info("Loading COGs")
    return_values = get_values_from_multiple_stac_items(
        stac_urls=stac_items, points=points, ds_args=ds_args
    )
    logger.info("Merging results into dict")
    return_json = merge_results_into_dict(return_values, points_json)
    return return_json


def process_request(
    points_json: dict,
    stac_items: list[str],
    workflow: bool = False,
    ds_args: str = None,
) -> dict:
    """
    Processes a request to get data values for points.

    Parameters:
    - points_json (dict): JSON containing points data.
    - stac_items (list[str]): List of STAC item IDs.

    Returns:
    dict: Response with status code and body.
    """
    if not all([points_json, stac_items]):
        return {"statusCode": 400, "body": json.dumps("Missing required parameters")}
    try:
        response = get_data_values(stac_items, points_json, ds_args)
        if workflow:
            return response
        else:
            try:
                return {"statusCode": 200, "body": json.dumps(response)}
            except Exception as e:
                logger.error("Error when returning response: %s", e)
                return {"statusCode": 500, "body": json.dumps(str(e))}
    except Exception as e:
        logger.error("Error processing request: %s", e)
        logger.debug("Stack trace: %s", traceback.format_exc())
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
    parser.add_argument("--assets", type=str, help="GeoJSON string with points data")
    parser.add_argument(
        "--stac_query", type=str, help="Query to pass to stac", default=None
    )
    parser.add_argument(
        "--token", type=str, help="Token to authenticate to STAC catalog", default=None
    )
    parser.add_argument("--stac_catalog", type=str, help="STAC catalog URL")
    parser.add_argument("--stac_collection", type=str, help="STAC collection ID")
    parser.add_argument("--start_date", type=str, help="Start date for STAC search")
    parser.add_argument("--end_date", type=str, help="End date for STAC search")
    parser.add_argument(
        "--max_items", type=int, help="Maximum number of items to return", default=None
    )
    parser.add_argument("--ds_args", type=str, help="Dataset arguments", default=None)
    return parser.parse_args()


def response_to_csv(in_json: dict, out_csv: str) -> None:
    """
    Converts a JSON response to a CSV file with columns for every datetime,
    a row for every id, and values of 'value'.

    Parameters:
    in_json (dict): The input JSON data.
    out_csv (str): The output CSV file path.
    """
    try:
        data = []
        for feature in in_json.get("features", []):
            feature_id = feature["properties"]["id"]
            for dt, values in feature["properties"]["returned_values"].items():
                data.append(
                    {"id": feature_id, "datetime": dt, "value": values.get("value")}
                )

        df = pd.DataFrame(data)
        logger.info("CSV File data: %s", df)
        pivot_df = df.pivot_table(index="id", columns="datetime", values="value")
        pivot_df.reset_index(inplace=True)

        # Ensure all datetime columns are included
        all_datetimes = sorted(df["datetime"].unique())
        pivot_df = pivot_df.reindex(columns=["id"] + all_datetimes, fill_value=None)

        pivot_df = pivot_df.astype(object).where(pd.notnull(pivot_df), None)
        pivot_df.fillna("null", inplace=True)
        pivot_df.to_csv(out_csv, index=False)
        logger.info("CSV file successfully created at %s", out_csv)
    except Exception as e:
        logger.error("An error occurred: %s", e)
        raise


def load_json_from_file(file_path):
    """
    Loads JSON content from a file and returns it as a dictionary.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The JSON content as a dictionary.

    Raises:
        RuntimeError: If the file is empty or contains invalid JSON.
    """
    with open(file_path, encoding="utf-8") as file:
        content = file.read()
        if not content.strip():
            raise RuntimeError(f"The JSON file {file_path} is empty.")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Failed to decode the content of the JSON file {file_path}"
            ) from exc


def download_points_file(args, temp_file: str) -> dict:
    """
    Download a points file from an HTTP URL or an S3 bucket and load its JSON content.

    Args:
        args: An object containing the arguments, including the JSON file path or URL.
        temp_file: A temporary file object to store the downloaded content.

    Returns:
        dict: The JSON content loaded from the downloaded file.
    """
    s3 = boto3.client("s3")

    file_name = args.assets
    if file_name.startswith("http"):
        logger.info(f"Downloading {file_name} using http...")
        response = requests.get(file_name)
        temp_file.write(response.text)
        temp_file.close()
        arg_points_json = load_json_from_file(temp_file.name)
    else:
        base_name = os.path.basename(file_name)
        user = file_name.split("/")[0]
        bucket_arn = (
            "arn:aws:s3:eu-west-2:312280911266:accesspoint/"
            f"eodhp-test-gstjkhpo-{user}-s3"
        )
        logger.info(f"Downloading {file_name} from {bucket_arn}...")

        # Use pathlib.Path to get the name without suffix
        s3.download_file(bucket_arn, file_name, base_name)
        arg_points_json = load_json_from_file(base_name)
    return arg_points_json


if __name__ == "__main__":
    logger.info("Starting the workflow")
    args = parse_arguments()

    os.environ["STAC_API_KEY"] = args.token

    stac_query = process_stac_query_args(args.stac_query)
    # logger.debug("STAC query: %s", stac_query)

    time_range = f"{args.start_date}/{args.end_date}"

    stac_items = search_stac(
        time_range=time_range,
        query=stac_query,
        catalog_url=args.stac_catalog,
        collection=args.stac_collection,
        max_items=args.max_items,
    )
    logger.debug("STAC items: %s", stac_items)

    # create a temporary file to store the points
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        try:
            logger.info("Downloading points file")
            arg_points_json = download_points_file(args, temp_file)
            logger.debug("Points JSON: %s", arg_points_json)
        except RuntimeError as e:
            logger.error(e)
            sys.exit(1)
    logger.info("Processing request")
    ds_args = ast.literal_eval(args.ds_args) if args.ds_args else None
    process_response = process_request(
        points_json=arg_points_json,
        stac_items=stac_items,
        workflow=True,
        ds_args=ds_args,
    )
    logger.debug("Process response: %s", process_response)
    # Make a stac catalog.json file to satitsfy the process runner
    out_name = "./data.csv"
    response_to_csv(process_response, out_name)

    with open("./catalog.json", "w", encoding="utf-8") as f:
        catalog = createStacCatalogRoot(outName=out_name)
        catalog["data"] = process_response
        try:
            json.dump(catalog, f)
        except Exception as e:
            print("Error writing catalog.json file: %s", e)

    with open("./data.json", "w", encoding="utf-8") as f:
        stacitem = createStacItem(outName=out_name)
        try:
            json.dump(stacitem, f)
        except Exception as e:
            print("Error writing data.json file: %s", e)
