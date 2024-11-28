"""
FastAPI app for local API
"""

from fastapi import FastAPI, HTTPException
from getassetvalues.main import get_data_values
from pydantic import BaseModel
from stac_items import default_stac_items

app = FastAPI()


class GetValuesInput(BaseModel):
    """
    Defines input schema for fetching data values.

    Attributes:
        stac_items (list[str]): List of STAC item IDs.
        points_json (dict): GeoJSON object with points.
    """

    stac_items: list[str] = default_stac_items
    points_json: dict


@app.post("/get-data-values/")
async def get_data_values_endpoint(input_json: GetValuesInput):
    """
    Endpoint to retrieve data values for given STAC items and points.

    This endpoint processes a request containing STAC items and
    geographic points, returning the corresponding data values.

    Args:
        input_json (getValuesInput): Input containing STAC items and
                                     points in GeoJSON format.

    Returns:
        The data values retrieved for the specified STAC items and
        points.

    Raises:
        HTTPException: An error occurred processing the request.
    """
    try:
        result = get_data_values(
            stac_items=input_json.stac_items, points_json=input_json.points_json
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
