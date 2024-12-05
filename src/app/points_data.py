import json
import os
import tempfile

import boto3
import numpy as np
import requests
import xarray as xr

from app.get_values_logger import logger


class SpatialData:
    def __init__(self, source: str):
        self.source = source
        self.data = self.download()

    def load_json_from_file(self, file_path: str) -> dict:
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

    def download(self) -> dict:
        """
        Download a spatial file from an HTTP URL or an
        S3 bucket and load its JSON content.

        Args:

        Returns:
            dict: The JSON content loaded from the downloaded file.
        """
        s3 = boto3.client("s3")

        if self.source.startswith("http"):
            logger.info(f"Downloading {self.source} using http...")
            response = requests.get(self.source)
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
                try:
                    logger.info("Downloading file")
                    temp_file.write(response.text)
                    temp_file.close()
                except RuntimeError as e:
                    logger.error(e)
            self.data = self.load_json_from_file(temp_file.name)
        else:
            base_name = os.path.basename(self.source)
            user = self.source.split("/")[0]
            bucket_arn = (
                "arn:aws:s3:eu-west-2:312280911266:accesspoint/"
                f"eodhp-test-gstjkhpo-{user}-s3"
            )
            logger.info(f"Downloading {self.source} from {bucket_arn}...")

            # Use pathlib.Path to get the name without suffix
            s3.download_file(bucket_arn, self.source, base_name)
            self.data = self.load_json_from_file(base_name)
        return self.data

    def spatial_to_xr_dataset(self) -> xr.Dataset:
        """
        Converts points data to an xarray Dataset.

        Returns:
        xr.Dataset: Dataset with points as coordinates.

        Raises:
        ValueError: If the input data is missing or invalid.
        """
        logger.info("Converting points to xarray Dataset")
        try:
            features = self.data["features"]
            latitudes = np.array(
                [feature["geometry"]["coordinates"][1] for feature in features]
            )
            longitudes = np.array(
                [feature["geometry"]["coordinates"][0] for feature in features]
            )
        except (KeyError, TypeError, IndexError) as e:
            logger.error(f"Invalid points data: {e}")
            raise ValueError("Invalid points data") from e

        dataset = xr.Dataset(
            {"x": (["points"], longitudes), "y": (["points"], latitudes)},
        )
        return dataset
