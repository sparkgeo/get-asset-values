"""
FastAPI app for local API
"""

from fastapi import FastAPI, HTTPException
from main import get_data_values
from pydantic import BaseModel, Field

app = FastAPI()


class Point(BaseModel):
    latitude: float = Field(..., alias="lat")
    longitude: float = Field(..., alias="lon")


class PointsInput(BaseModel):
    points: list[dict]
    latitude_key: str
    longitude_key: str


class StacItemsInput(BaseModel):
    stac_items: list[str]


@app.post("/get-data-values/")
async def get_data_values_endpoint(
    stac_items_input: StacItemsInput, points_input: PointsInput
):
    try:
        result = get_data_values(
            stac_items=stac_items_input.stac_items,
            points_json=points_input.points,
            latitude_key=points_input.latitude_key,
            longitude_key=points_input.longitude_key,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
