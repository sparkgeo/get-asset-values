import datetime as dt
from pathlib import Path
from unittest.mock import mock_open, patch

from app.stac_code.create_stac import (
    createStacCatalogRoot,
    createStacItem,
)


@patch("app.stac_code.create_stac.os.path.getsize")
@patch("app.stac_code.create_stac.mimetypes.guess_type")
@patch("app.stac_code.create_stac.time.time_ns")
@patch("app.stac_code.create_stac.open", new_callable=mock_open)
def test_createStacItem(mock_open, mock_time_ns, mock_guess_type, mock_getsize):
    # Mock the return values
    mock_time_ns.return_value = 1633036800000000000  # Mocked timestamp
    mock_guess_type.return_value = ("application/json", None)
    mock_getsize.return_value = 12345

    outName = "test_output.json"
    expected_stem = Path(outName).stem
    expected_now = mock_time_ns.return_value / 1_000_000_000
    expected_dateNow = (
        dt.datetime.fromtimestamp(expected_now).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    )
    expected_size = mock_getsize.return_value
    expected_mime = mock_guess_type.return_value[0]

    expected_data = {
        "stac_version": "1.0.0",
        "id": f"{expected_stem}-{expected_now}",
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[-180, -90], [-180, 90], [180, 90], [180, -90], [-180, -90]]
            ],
        },
        "properties": {
            "created": f"{expected_dateNow}",
            "datetime": f"{expected_dateNow}",
            "updated": f"{expected_dateNow}",
        },
        "bbox": [-180, -90, 180, 90],
        "assets": {
            f"{expected_stem}": {
                "type": f"{expected_mime}",
                "roles": ["data"],
                "href": f"{outName}",
                "file:size": expected_size,
            }
        },
        "links": [
            {"type": "application/json", "rel": "parent", "href": "catalog.json"},
            {
                "type": "application/geo+json",
                "rel": "self",
                "href": f"{expected_stem}.json",
            },
            {"type": "application/json", "rel": "root", "href": "catalog.json"},
        ],
    }

    result = createStacItem(outName)
    assert result == expected_data


def test_createStacCatalogRoot():
    outName = "test_output.json"
    expected_stem = Path(outName).stem

    expected_data = {
        "stac_version": "1.0.0",
        "id": "catalog",
        "type": "Catalog",
        "description": "Root catalog",
        "links": [
            {
                "type": "application/geo+json",
                "rel": "item",
                "href": f"{expected_stem}.json",
            },
            {"type": "application/json", "rel": "self", "href": "catalog.json"},
        ],
    }

    result = createStacCatalogRoot(outName)
    assert result == expected_data
