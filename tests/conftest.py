"""Shared pytest fixtures."""
import sys
from pathlib import Path

# Ensure repo root on sys.path so `import app` and `from src...` work.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from src.coordinate_parser import Coordinate, save_coordinates


@pytest.fixture
def sample_coords():
    return [
        Coordinate(
            latitude=23.0, longitude=5.0, name="Test site",
            address="Sahara", date_saved="2024-01-01", source_url="",
            category="site", notes="",
        ),
        Coordinate(
            latitude=15.5, longitude=10.2, name="Unreviewed",
            address="", date_saved="", source_url="", category="uncategorized",
        ),
    ]


@pytest.fixture
def temp_data_file(tmp_path, sample_coords):
    f = tmp_path / "coords.json"
    save_coordinates(sample_coords, f)
    return f


@pytest.fixture
def client(tmp_path, monkeypatch, sample_coords):
    """Flask test client with isolated data file."""
    data_file = tmp_path / "africa_coordinates.json"
    save_coordinates(sample_coords, data_file)

    import app as app_module
    monkeypatch.setattr(app_module, "COORDS_FILE", data_file)
    monkeypatch.setattr(app_module, "DATA_DIR", tmp_path)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c
