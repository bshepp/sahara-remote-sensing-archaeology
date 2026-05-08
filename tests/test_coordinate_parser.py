"""Tests for src/coordinate_parser.py."""
import json
from pathlib import Path

import pytest

from src.coordinate_parser import (
    Coordinate,
    extract_coords_from_url,
    filter_africa_coordinates,
    is_in_africa,
    load_coordinates,
    parse_google_places_json,
    save_coordinates,
)


class TestIsInAfrica:
    def test_sahara_point(self):
        assert is_in_africa(23.0, 5.0)

    def test_cape_town(self):
        assert is_in_africa(-33.9, 18.4)

    def test_paris_excluded(self):
        assert not is_in_africa(48.85, 2.35)

    def test_antarctica_excluded(self):
        assert not is_in_africa(-80.0, 0.0)

    def test_boundaries_inclusive(self):
        assert is_in_africa(-35.0, -25.0)
        assert is_in_africa(37.5, 55.0)


class TestExtractCoordsFromUrl:
    def test_basic_url(self):
        assert extract_coords_from_url(
            "https://maps.google.com/?q=21.012128,51.250482"
        ) == (21.012128, 51.250482)

    def test_negative(self):
        assert extract_coords_from_url("?q=-12.5,-7.25") == (-12.5, -7.25)

    def test_no_match(self):
        assert extract_coords_from_url("https://example.com") is None

    def test_empty(self):
        assert extract_coords_from_url("") is None
        assert extract_coords_from_url(None) is None


class TestParseGooglePlacesJson:
    def test_parses_valid_features(self, tmp_path):
        data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "geometry": {"type": "Point", "coordinates": [5.0, 23.0]},
                    "properties": {
                        "location": {"name": "X", "address": "A"},
                        "date": "2024-01-01",
                        "google_maps_url": "",
                    },
                }
            ],
        }
        f = tmp_path / "in.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        coords = parse_google_places_json(f)
        assert len(coords) == 1
        c = coords[0]
        # GeoJSON is [lon, lat] — make sure parser keeps that straight.
        assert c.latitude == 23.0
        assert c.longitude == 5.0
        assert c.name == "X"

    def test_falls_back_to_url_for_zero_zero(self, tmp_path):
        data = {
            "features": [
                {
                    "geometry": {"coordinates": [0, 0]},
                    "properties": {
                        "location": {},
                        "google_maps_url": "?q=17.09,7.94",
                    },
                }
            ]
        }
        f = tmp_path / "in.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        coords = parse_google_places_json(f)
        assert len(coords) == 1
        assert coords[0].latitude == 17.09
        assert coords[0].longitude == 7.94

    def test_skips_unrecoverable_zero_zero(self, tmp_path):
        data = {
            "features": [
                {
                    "geometry": {"coordinates": [0, 0]},
                    "properties": {"location": {}, "google_maps_url": ""},
                }
            ]
        }
        f = tmp_path / "in.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        assert parse_google_places_json(f) == []


class TestFilterAfricaCoordinates:
    def test_filters_out_non_africa(self):
        coords = [
            Coordinate(23.0, 5.0, "in", "", "", ""),
            Coordinate(48.85, 2.35, "out", "", "", ""),
        ]
        result = filter_africa_coordinates(coords)
        assert len(result) == 1
        assert result[0].name == "in"


class TestSaveLoadRoundtrip:
    def test_roundtrip_preserves_data(self, tmp_path, sample_coords):
        f = tmp_path / "out.json"
        save_coordinates(sample_coords, f)
        loaded = load_coordinates(f)
        assert len(loaded) == len(sample_coords)
        assert loaded[0].name == sample_coords[0].name
        assert loaded[0].category == "site"

    def test_save_creates_backup_on_overwrite(self, tmp_path, sample_coords):
        f = tmp_path / "out.json"
        save_coordinates(sample_coords, f)
        assert not f.with_suffix(".json.bak").exists()
        # Second save should rotate the prior file to .bak.
        save_coordinates(sample_coords[:1], f)
        assert f.with_suffix(".json.bak").exists()
        assert len(load_coordinates(f)) == 1

    def test_load_missing_returns_empty(self, tmp_path):
        assert load_coordinates(tmp_path / "nope.json") == []
