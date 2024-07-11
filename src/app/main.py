from src.app.get_values import get_values_from_multiple_cogs, merge_results_into_dict
from src.app.get_values_logger import logger
from src.app.load_cogs import load_multiple_cogs
from src.app.load_points import check_json, points_to_xr_dataset


def get_data_values(
    cog_files: list[str], points_json: dict, latitude_key: str, longitude_key: str
):
    cog_dss = load_multiple_cogs(cog_files)
    check_json(points_json, latitude_key, longitude_key)
    points = points_to_xr_dataset(points_json, latitude_key, longitude_key)
    return_values = get_values_from_multiple_cogs(datasets=cog_dss, points=points)
    return_json = merge_results_into_dict(return_values, points_json)
    return return_json
