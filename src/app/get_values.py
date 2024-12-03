"""
Functions to get values from a cog file
"""

import rasterio as rio
import rioxarray as rxr
import xarray as xr
from dateutil.parser import parse
from pyproj import Transformer
from rasterio.session import AWSSession
from shortuuid import ShortUUID

from app.get_values_logger import logger
from app.stac_code.stac_parsing import get_asset_details, get_stac_item

aws_session = AWSSession(aws_unsigned=True)


def determine_file_type(url: str) -> str:
    """
    Determines the file type based on the URL extension.

    Parameters:
    - url (str): URL of the file.

    Returns:
    str: The type of the file ('GeoTIFF', 'JSON', 'NetCDF', or 'Unknown').
    """
    if url.endswith(".tif") or url.endswith(".tiff"):
        return "GeoTIFF"
    elif url.endswith(".json"):
        return "JSON"
    elif url.endswith(".nc"):
        return "NetCDF"
    else:
        return "Unknown"


def open_dataset(stac_details: dict, ds_args) -> xr.Dataset:
    """
    Opens a dataset from a URL.

    Parameters:
    - url (str): URL to open.
    - crs (str | None): Coordinate reference system to write to the dataset.
    Default is None.
    - variable (str | None): Specific variable to extract from the dataset.
    Default is None.

    Returns:
    xr.Dataset: Dataset opened from URL.
    """
    logger.info("Opening dataset from URL")
    url = stac_details["url"]
    if isinstance(ds_args, dict):
        variable = ds_args.get("variable", None)
        crs = ds_args.get("crs", None)
    else:
        variable = None
        crs = None
    file_type = determine_file_type(url)
    try:
        match file_type:
            case "JSON":
                logger.info("Opening JSON file")
                ds = xr.open_dataset(url, decode_coords="all", engine="kerchunk")
                if variable:
                    ds = ds[variable]
            case "NetCDF":
                logger.info("Opening NetCDF file")
                ds = xr.open_dataset(url, decode_coords="all")
                if variable:
                    ds = ds[variable]
            case "GeoTIFF":
                logger.info("Opening GeoTIFF file")
                ds = rxr.open_rasterio(url, mask_and_scale=True)
            case _:
                raise ValueError(f"Unsupported file type: {file_type}")
        ds.attrs["file_path"] = url
        if crs:
            ds.rio.write_crs(crs, inplace=True)
        else:
            if not ds.rio.crs:
                logger.info("CRS not found in dataset. Writing default CRS.")
                ds.rio.write_crs("EPSG:4326", inplace=True)
        return ds
    except Exception as e:
        logger.error(f"Failed to open dataset from URL: {url}. Error: {e}")
        raise e


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


def get_values_from_stac(stac_url: list[str], points: xr.Dataset, ds_args) -> dict:
    """
    Retrieves values from a COG file for given points.

    Parameters:
    - stac_item (dict): STAC item with COG URL.
    - points (xr.Dataset): Dataset of points to extract values for.

    Returns:
    dict: A dictionary with file path and values.
    """
    logger.info("Getting values from STAC item.")
    stac_item = get_stac_item(stac_url)
    logger.info("Got STAC item")
    stac_details = get_asset_details(stac_item)
    logger.info("STAC details: %s", stac_details)
    ds = open_dataset(stac_details, ds_args)
    values = get_values(ds, points)
    return {"stac_details": stac_details, "values": values}


def get_values_from_multiple_stac_items(
    stac_urls: list[str], points: xr.Dataset, ds_args: str = None
) -> list:
    """
    Retrieves values from multiple COG files for given points.

    Parameters:
    - datasets (list[xr.DataArray]): List of data arrays.
    - points (xr.Dataset): Dataset of points to extract values for.

    Returns:
    list: A list of dictionaries with file paths and values.
    """
    logger.info("Getting values from multiple COG files")
    return_values = []
    for ds in stac_urls:
        return_values.append(get_values_from_stac(ds, points, ds_args))
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
        dt = result["stac_details"]["datetime"]
        # dt in YYYY-MM-DD HH:MM format
        logger.info("Datetime: %s", dt)
        dt_string = parse(dt).strftime("%Y-%m-%d %H:%M")
        logger.info("Datetime string: %s", dt_string)
        file_name = result["stac_details"]["source_file_name"]
        unit = result["stac_details"].get("unit", "none")
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
