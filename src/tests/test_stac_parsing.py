from app.stac_parsing import get_asset_details


def test_get_asset_details():
    """
    Test get_asset_details function with a valid STAC item.
    """
    stac_item = {
        "assets": {
            "asset1": {"type": "image/tiff", "href": "https://example.com/asset1.tif"},
            "asset2": {
                "type": "application/zstd",
                "href": "https://example.com/asset2.zstd",
            },
        },
        "properties": {"datetime": "2024-02-01T00:00:00Z", "unit": "c"},
    }

    expected_result = {
        "url": "https://example.com/asset1.tif",
        "datetime": "2024-02-01T00:00:00Z",
        "source_file_name": "asset1",
        "unit": "c",
    }

    result = get_asset_details(stac_item)

    print(f"result: {result}")
    print(f"expected_result: {expected_result}")
    assert result == expected_result


def test_get_asset_details_no_matching_asset():
    """
    Test get_asset_details function with no matching asset type.
    """
    stac_item = {
        "assets": {
            "asset1": {
                "type": "application/json",
                "href": "https://example.com/asset1.txt",
            }
        },
        "properties": {"datetime": "2024-02-01T00:00:00Z", "unit": "c"},
    }

    result = get_asset_details(stac_item)
    assert result is None


def test_get_asset_details_missing_unit():
    """
    Test get_asset_details function with a missing unit property.
    """
    stac_item = {
        "assets": {
            "asset1": {"type": "image/tiff", "href": "https://example.com/asset1.tif"}
        },
        "properties": {"datetime": "2024-02-01T00:00:00Z"},
    }

    expected_result = {
        "url": "https://example.com/asset1.tif",
        "datetime": "2024-02-01T00:00:00Z",
        "source_file_name": "asset1",
        "unit": None,
    }

    result = get_asset_details(stac_item)
    assert result == expected_result
