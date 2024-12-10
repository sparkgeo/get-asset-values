#!/usr/bin/env python3
"""
Main starting point for the workflow.
"""

import argparse

from app.create_response import ResponseStatus, WorkflowResponse
from app.extra import string_to_json
from app.get_values import get_values_for_multiple_stac_assets
from app.get_values_logger import logger
from app.points_data import SpatialData
from app.search_stac import StacSearch
from app.stac_parsing import get_asset_data_list


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
    parser.add_argument(
        "--extra_args", type=str, help="Extra arguments for the workflow", default=None
    )
    args = parser.parse_args()

    logger.info("Extra arguments: %s", args.extra_args)

    args.extra_args = string_to_json(args.extra_args) if args.extra_args else None
    logger.info("Parsed extra arguments: %s", args.extra_args)
    args.stac_query = string_to_json(args.stac_query) if args.stac_query else None

    return args


def run_workflow(args: argparse.Namespace) -> None:
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
        WorkflowResponse(status=ResponseStatus.ERROR, error_msg="No STAC items found")
    else:
        logger.info("Found STAC items, getting points data")
        spatial_data = SpatialData(args.assets)

        logger.info("Getting asset data list")
        asset_data_list = get_asset_data_list(stac_search.results)

        logger.info("Getting values from STAC items")
        return_values = get_values_for_multiple_stac_assets(
            asset_details_list=asset_data_list,
            points=spatial_data.spatial_to_xr_dataset(),
            extra_args=args.extra_args,
        )
        logger.info("Merging results into dict")

        logger.debug("Returned values: %s", return_values)
        WorkflowResponse(
            return_values=return_values,
            status=ResponseStatus.SUCCESS,
            points_json=spatial_data.data,
            extra_args=args.extra_args,
        )


if __name__ == "__main__":
    logger.info("Starting the workflow")
    args = parse_arguments()
    run_workflow(args)
