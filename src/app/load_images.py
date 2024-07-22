"""
Functions to load cog files into a dataset
"""

import os

import rasterio as rio
import rioxarray as rxr
import xarray as xr
from get_values_logger import logger
from rasterio.session import AWSSession

aws_session = AWSSession(aws_unsigned=True)


def load_cog(file_path: str) -> xr.DataArray:
    """
    Loads a single COG file into an xarray.DataArray.

    Parameters:
    - file_path (str): Path to the COG file.

    Returns:
    xr.DataArray: Data array with COG file data.
    """
    logger.info("Loading COG file from %s", file_path)
    with rio.Env(aws_session):
        ds = rxr.open_rasterio(file_path, mask_and_scale=True)
        ds.attrs["file_path"] = file_path
    return ds


def load_zarr(file_path: str) -> xr.DataArray:
    """
    Loads a single Zarr file into an xarray.DataArray.

    Parameters:
    - file_path (str): Path to the Zarr file.

    Returns:
    xr.DataArray: Data array with Zar file data.
    """
    logger.info("Loading Zarr file from %s", file_path)
    with rio.Env(aws_session):
        ds = xr.open_zarr(file_path, mask_and_scale=True)
        ds.attrs["file_path"] = file_path
    ds = ds[list(ds.data_vars)[0]]  # Select first data variable
    # TODO: Add support for multiple variables
    return ds


def load_multiple_cogs(file_paths: list[str]) -> list[xr.DataArray]:
    """
    Loads multiple files into xarray.DataArrays.

    Parameters:
    - file_paths (list[str]): Paths to files.

    Returns:
    list[xr.DataArray]: List of data arrays from COG/Zarr files.
    """
    logger.info("Loading files")
    datasets = []
    for file_path in file_paths:
        if file_path.endswith((".tif", ".tiff")):
            ds = load_cog(file_path)
            datasets.append(ds)
        elif file_path.endswith(".zarr") or os.path.isdir(file_path):
            ds = load_zarr(file_path)
            datasets.append(ds)
        else:
            logger.warning(f"Unsupported file format: {file_path}")
    return datasets
