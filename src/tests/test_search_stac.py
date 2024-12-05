from unittest.mock import MagicMock, patch

import pytest

from app.search_stac import (
    get_search_results,
    open_catalog,
    process_stac_query_args,
    query_to_filter,
    search_catalog,
)


@patch("app.stac_code.search_stac.pystac_client.Client.open")
def test_open_catalog(mock_client_open):
    # Mock the return values
    mock_catalog = MagicMock()
    mock_client_open.return_value = mock_catalog

    catalog_url = "https://example.com/stac_catalog"
    result = open_catalog(catalog_url)

    # Assertions
    mock_client_open.assert_called_once_with(
        catalog_url,
    )
    assert result == mock_catalog


def test_query_to_filter():
    query = {"day_night": "DAY", "unit": "c"}

    expected_filter = {
        "op": "and",
        "args": [
            {
                "op": "=",
                "args": [{"property": "properties.day_night"}, "DAY"],
            },
            {
                "op": "=",
                "args": [{"property": "properties.unit"}, "c"],
            },
        ],
    }

    result = query_to_filter(query)
    assert result == expected_filter


@patch("app.stac_code.search_stac.query_to_filter")
def test_search_catalog(mock_query_to_filter):
    # Mock the return value of query_to_filter
    mock_query_to_filter.return_value = {
        "op": "and",
        "args": [
            {
                "op": "=",
                "args": [{"property": "properties.day_night"}, "DAY"],
            },
            {
                "op": "=",
                "args": [{"property": "properties.unit"}, "c"],
            },
        ],
    }

    # Mock the catalog client
    mock_catalog = MagicMock()
    mock_search = MagicMock()
    mock_catalog.search.return_value = mock_search

    # Test parameters
    time_range = "2024-02-01T00:00:00Z/2024-02-28T23:59:59Z"
    query = {"day_night": "DAY", "unit": "c"}
    collection = "example-collection"
    max_items = 10

    # Expected search parameters
    expected_search_params = {
        "datetime": time_range,
        "filter": mock_query_to_filter.return_value,
        "collections": [collection],
        "max_items": max_items,
    }

    # Call the function
    result = search_catalog(mock_catalog, time_range, query, collection, max_items)

    # Assertions
    mock_query_to_filter.assert_called_once_with(query)
    mock_catalog.search.assert_called_once_with(**expected_search_params)
    assert result == mock_search


def test_get_search_results():
    # Mock the search result items
    mock_item1 = MagicMock()
    mock_item1.get_self_href.return_value = "https://example.com/item1"
    mock_item2 = MagicMock()
    mock_item2.get_self_href.return_value = "https://example.com/item2"

    # Mock the search object
    mock_search = MagicMock()
    mock_search.items.return_value = [mock_item1, mock_item2]

    # Expected result
    expected_result = ["https://example.com/item1", "https://example.com/item2"]

    # Call the function
    result = get_search_results(mock_search)

    # Assertions
    mock_search.items.assert_called_once()
    assert result == expected_result


@patch(
    "sys.argv",
    [
        "search_stac.py",
        "--time_range",
        "2024-02-01T00:00:00Z/2024-02-28T23:59:59Z",
        "--query",
        "{'day_night': 'DAY', 'unit': 'c'}",
        "--catalog_url",
        "https://example.com/stac_catalog",
        "--collection",
        "example-collection",
        "--max_items",
        "10",
    ],
)
def test_process_stac_query_args_valid_json():
    stac_query = '{"day_night": "DAY", "unit": "c"}'
    expected_result = {"day_night": "DAY", "unit": "c"}

    result = process_stac_query_args(stac_query)
    assert result == expected_result


def test_process_stac_query_args_valid_literal():
    stac_query = "{'day_night': 'DAY', 'unit': 'c'}"
    expected_result = {"day_night": "DAY", "unit": "c"}

    result = process_stac_query_args(stac_query)
    assert result == expected_result


def test_process_stac_query_args_invalid_format():
    stac_query = "invalid_query"

    with pytest.raises(ValueError, match="Invalid stac_query format"):
        process_stac_query_args(stac_query)


def test_process_stac_query_args_missing_query():
    stac_query = None
    result = process_stac_query_args(stac_query)
    assert result is None
