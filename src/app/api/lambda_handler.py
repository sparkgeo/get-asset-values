"""
This module defines the AWS Lambda function handler for processing requests
to fetch data values based on geographic points and STAC items.
"""

import json

from get_values_logger import logger
from getassetvalues.main import process_request


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
    return process_request(points_json, stac_items)
