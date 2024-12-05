import ast
import json

from app.get_values_logger import logger


def string_to_json(string: str) -> dict | None:
    """
    Converts a string to a JSON object.

    Args:
        string (str): The string to convert.

    Returns:
        dict | None: The JSON object if conversion is successful, None otherwise.
    """
    try:
        return json.loads(string)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(string)
        except (ValueError, SyntaxError) as ast_err:
            logger.error(f"ast.literal_eval failed: {ast_err}")
            return None
