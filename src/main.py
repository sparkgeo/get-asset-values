#!/usr/bin/env python3
"""
Main starting point for the workflow.
"""

import argparse
import ast
import json
import traceback

from app.create_response import ResponseStatus, WorkflowResponse
from app.get_values import get_values_from_multiple_stac_items, merge_results_into_dict
from app.get_values_logger import logger
from app.points_data import PointsData
from app.stac_code.search_stac import StacSearch


def get_data_values(
    stac_items: list[str], points: PointsData, ds_args: str = None
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
    logger.info("Loading COGs")
    return_values = get_values_from_multiple_stac_items(
        stac_urls=stac_items, points=points.points_to_xr_dataset(), ds_args=ds_args
    )
    logger.info("Merging results into dict")
    return_json = merge_results_into_dict(return_values, points.data)
    return return_json


def process_request(
    points: PointsData,
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
    if not all([points, stac_items]):
        return {"statusCode": 400, "body": json.dumps("Missing required parameters")}
    try:
        response = get_data_values(stac_items, points, ds_args)
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
    parser.add_argument("--stac_catalog", type=str, help="STAC catalog URL")
    parser.add_argument("--stac_collection", type=str, help="STAC collection ID")
    parser.add_argument("--start_date", type=str, help="Start date for STAC search")
    parser.add_argument("--end_date", type=str, help="End date for STAC search")
    parser.add_argument(
        "--max_items", type=int, help="Maximum number of items to return", default=None
    )
    parser.add_argument("--ds_args", type=str, help="Dataset arguments", default=None)
    args = parser.parse_args()
    try:
        args.ds_args = ast.literal_eval(args.ds_args) if args.ds_args else None
    except (ValueError, SyntaxError) as e:
        logger.error(f"Error parsing ds_args: {e}")
        args.ds_args = None
    return args


if __name__ == "__main__":
    logger.info("Starting the workflow")
    args = parse_arguments()

    stac_search = StacSearch(
        catalog_url=args.stac_catalog,
        start_date=args.start_date,
        end_date=args.end_date,
        stac_query=args.stac_query,
        collection=args.stac_collection,
        max_items=args.max_items,
    )

    if stac_search.number_of_results == 0:
        logger.error("No STAC items found")
        response = WorkflowResponse(
            status=ResponseStatus.ERROR,
            error_msg="No STAC items found",
            process_response={},
        )
    else:
        logger.info("Found STAC items")
        points_data = PointsData(args.assets)

        logger.info("Processing request")

        process_response = process_request(
            points=points_data,
            stac_items=stac_search.results,
            workflow=True,
            ds_args=args.ds_args,
        )
        logger.debug("Process response: %s", process_response)
        response = WorkflowResponse(
            process_response=process_response,
            status=ResponseStatus.SUCCESS,
        )
