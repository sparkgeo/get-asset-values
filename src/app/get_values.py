"""
Functions to get values from a cog file
"""

import rasterio as rio
import xarray as xr
from dateutil.parser import parse
from pyproj import Transformer
from rasterio.session import AWSSession
from shortuuid import ShortUUID

from app.create_dataarray import AssetDataArray
from app.get_values_logger import logger
from app.stac_parsing import AssetDetails

aws_session = AWSSession(aws_unsigned=True)


def get_values(ds: xr.DataArray, points: xr.Dataset) -> list:
    """
    Extracts values from a COG file for specified points.

    Parameters:
    - ds (xr.DataArray): Data array to extract values from.
    - points (xr.Dataset): Dataset containing points of interest.

    Returns:
    list: A list containing the file path and extracted values,
    replacing NaNs with None.
    """
    logger.info("Getting values from COG file")
    with rio.Env(aws_session):
        ds_crs = ds.rio.crs
        if ds_crs == "EPSG:4326":
            logger.info("Dataset CRS is EPSG:4326")
            points_transformed = points
        else:
            logger.info("Transforming points to dataset CRS")
            transformer = Transformer.from_crs("EPSG:4326", ds_crs, always_xy=True)
            x_t, y_t = transformer.transform(points.x, points.y)  # pylint: disable=E0633
            points_transformed = xr.Dataset(
                {"x": (["points"], x_t), "y": (["points"], y_t)},
            )
        index_keys = list(ds._indexes.keys())
        logger.info(f"Index keys: {index_keys}")
        if "lat" in index_keys and "lon" in index_keys:
            logger.info("Using lat and lon as indexes")
            values = (
                ds.sel(
                    lat=points_transformed.y, lon=points_transformed.x, method="nearest"
                )
                .values[0]
                .tolist()
            )
        elif "y" in index_keys and "x" in index_keys:
            logger.info("Using y and x as indexes")
            values = (
                ds.sel(x=points_transformed.x, y=points_transformed.y, method="nearest")
                .values[0]
                .tolist()
            )
        else:
            logger.error("Unsupported index keys")
        # replace nan with None
        values = [None if str(v) == "nan" else v for v in values]
        return values


def get_values_for_multiple_stac_assets(
    asset_details_list: list[AssetDetails], points: xr.Dataset, extra_args: str = None
) -> list:
    logger.debug("Getting values from multiple files")
    return_values = []
    for asset_details in asset_details_list:
        logger.info("Getting values from multiple COG files")
        da = AssetDataArray(asset_details=asset_details, extra_args=extra_args).ds
        result = get_values(ds=da, points=points)
        return_values.append({"asset_details": asset_details, "values": result})
    return return_values


def merge_results_into_dict(results_list: list, request_json: dict) -> dict:
    """
    Merges extracted values into the original request JSON.

    Parameters:
    - results_list (list): List of dicts with file paths and values.
    - request_json (dict): Original request GeoJSON to merge results into.

    Returns:
    dict: The updated request JSON with merged results.
    """
    for feature in request_json["features"]:
        if "id" not in feature["properties"]:
            feature["properties"]["id"] = ShortUUID().random(length=8)
        feature["properties"]["returned_values"] = {}

    for result in results_list:
        dt = result["asset_details"].datetime
        # dt in YYYY-MM-DD HH:MM format
        logger.info("Datetime: %s", dt)
        dt_string = parse(dt).strftime("%Y-%m-%d %H:%M")
        logger.info("Datetime string: %s", dt_string)
        file_name = result["asset_details"].source_file_name
        unit = result["asset_details"].unit
        for index, value in enumerate(result["values"]):
            request_json["features"][index]["properties"]["returned_values"][
                dt_string
            ] = {
                "value": value,
                "datetime": dt,
                "unit": unit,
                "file_name": file_name,
            }
    return request_json
