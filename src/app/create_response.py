import datetime as dt
import json
import mimetypes
import os
import time
from pathlib import Path

import pandas as pd
from dateutil.parser import parse
from shortuuid import ShortUUID

from app.get_values_logger import logger


class ResponseStatus:
    SUCCESS = "success"
    ERROR = "error"


class WorkflowResponse:
    def __init__(
        self,
        status: ResponseStatus,
        return_values: dict = None,
        points_json: dict = None,
        error_msg=None,
        extra_args=None,
    ):
        self.status = status
        self.error_msg = error_msg
        self.extra_args = extra_args
        if self.status == ResponseStatus.ERROR:
            self.process_response = {}
            self.out_file = "./error.txt"
            self.create_error_response()
        else:
            self.process_response = self.merge_results_into_dict(
                return_values, points_json
            )
            self.points_json = points_json
            self.out_file = "./data.csv"
            self.to_csv()

        self.stac_item = self.createStacItem()
        self.stac_catalog_root = self.createStacCatalogRoot()
        self.write_stac_files()

    def createStacItem(self) -> dict:
        """
        Create a STAC (SpatioTemporal Asset Catalog)
        item from the given output file name

        Args:

        Returns:
            data (dict): The STAC item data.
        """
        stem = Path(self.out_file).stem
        now = time.time_ns() / 1_000_000_000
        dateNow = dt.datetime.fromtimestamp(now)
        dateNow = dateNow.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
        size = os.path.getsize(f"{self.out_file}")
        mime = mimetypes.guess_type(f"{self.out_file}")[0]
        data = {
            "stac_version": "1.0.0",
            "id": f"{stem}-{now}",
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[-180, -90], [-180, 90], [180, 90], [180, -90], [-180, -90]]
                ],
            },
            "properties": {
                "created": f"{dateNow}",
                "datetime": f"{dateNow}",
                "updated": f"{dateNow}",
            },
            "bbox": [-180, -90, 180, 90],
            "assets": {
                f"{stem}": {
                    "type": f"{mime}",
                    "roles": ["data"],
                    "href": f"{self.out_file}",
                    "file:size": size,
                }
            },
            "links": [
                {"type": "application/json", "rel": "parent", "href": "catalog.json"},
                {"type": "application/geo+json", "rel": "self", "href": f"{stem}.json"},
                {"type": "application/json", "rel": "root", "href": "catalog.json"},
            ],
        }
        return data

    def createStacCatalogRoot(self) -> dict:
        """
        Create the root STAC (SpatioTemporal Asset Catalog) catalog
        from the given output file name.

        Args:

        Returns:
            data (dict): The root STAC catalog data.
        """
        stem = Path(self.out_file).stem
        catalog = {
            "stac_version": "1.0.0",
            "id": "lst_results",
            "type": "Catalog",
            "title": "LST Results",
            "description": "Root catalog",
            "links": [
                {"type": "application/geo+json", "rel": "item", "href": f"{stem}.json"},
                {"type": "application/json", "rel": "self", "href": "catalog.json"},
            ],
        }
        catalog["data"] = self.process_response
        return catalog

    def write_stac_files(self):
        """
        Write the STAC item and catalog root to their respective JSON files.
        """
        try:
            json_to_file(self.stac_item, f"{Path(self.out_file).stem}.json")
            json_to_file(self.stac_catalog_root, "./catalog.json")
        except Exception as e:
            logger.error(f"Error writing STAC files: {e}")

    def to_csv(self) -> None:
        """
        Converts a JSON response to a CSV file with columns for every datetime,
        a row for every id, and values of 'value'.

        Parameters:
        process_response (dict): The input JSON data.
        out_csv (str): The output CSV file path.
        """
        try:
            data = []
            for feature in self.process_response.get("features", []):
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
            pivot_df.to_csv("./data.csv", index=False)
            logger.info("CSV file successfully created at %s", "./data.csv")
        except Exception as e:
            logger.error("An error occurred: %s", e)
            raise

    def create_error_response(self) -> dict:
        """
        Create an error response with the given error message.

        Args:
        error_msg (str): The error message.

        Returns:
        dict: The error response.
        """
        error_return = {
            "statusCode": 500,
            "body": {"error": self.error_msg},
        }
        json_to_file(error_return, self.out_file)

    def merge_results_into_dict(self, results_list: list, request_json: dict) -> dict:
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
            datetime_string = parse(dt).strftime("%Y-%m-%d %H:%M:%S")
            logger.info("Datetime string: %s", datetime_string)
            file_name = result["asset_details"].source_file_name
            logger.info("File name: %s", file_name)
            if self.extra_args and "unit" in self.extra_args:
                unit = self.extra_args["unit"]
            else:
                unit = result["asset_details"].unit
            if self.extra_args and "output_name" in self.extra_args:
                output_name = self.extra_args["output_name"]
                output_name = eval(f"f'{output_name}'")
            else:
                output_name = datetime_string[:-9]
            logger.info("Output name: %s", output_name)
            for index, value in enumerate(result["values"]):
                request_json["features"][index]["properties"]["returned_values"][
                    output_name
                ] = {
                    "value": value,
                    "datetime": dt,
                    "unit": unit,
                    "file_name": file_name,
                }

            for feature in request_json["features"]:
                feature["properties"]["returned_values"] = dict(
                    sorted(feature["properties"]["returned_values"].items())
                )
        return request_json


def json_to_file(json_data: dict, file_path: str) -> None:
    """
    Writes JSON data to a file.

    Args:
        json_data (dict): The JSON data to write.
        file_path (str): The path to the file where the JSON data will be written.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        try:
            json.dump(json_data, f)
        except Exception as e:
            print(f"Error writing data to file, {file_path}: {e}")
