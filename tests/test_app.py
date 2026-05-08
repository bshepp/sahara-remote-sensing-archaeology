"""Smoke tests for the Flask app."""
from src.coordinate_parser import load_coordinates


def test_index_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Test site" in r.data or b"site" in r.data


def test_api_coordinates(client):
    r = client.get("/api/coordinates")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 2
    assert data[0]["latitude"] == 23.0


def test_api_coordinates_filter(client):
    r = client.get("/api/coordinates?category=site")
    data = r.get_json()
    assert len(data) == 1
    assert data[0]["category"] == "site"


def test_export_geojson_uses_lon_lat_order(client):
    r = client.get("/export/site")
    assert r.status_code == 200
    fc = r.get_json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 1
    # GeoJSON spec: [lon, lat]
    assert fc["features"][0]["geometry"]["coordinates"] == [5.0, 23.0]


def test_review_get(client):
    r = client.get("/review/0")
    assert r.status_code == 200


def test_review_out_of_range_redirects(client):
    r = client.get("/review/999")
    assert r.status_code == 302


def test_review_update_persists(client, tmp_path, monkeypatch):
    import app as app_module
    r = client.post("/review/1", data={
        "action": "update",
        "latitude": "16.0",
        "longitude": "11.0",
        "category": "site",
        "notes": "found one",
        "name": "Updated",
        "filter_category": "uncategorized",
    })
    assert r.status_code == 302
    coords = load_coordinates(app_module.COORDS_FILE)
    assert coords[1].category == "site"
    assert coords[1].latitude == 16.0
    assert coords[1].name == "Updated"


def test_review_update_rejects_bad_coords(client):
    import app as app_module
    before = load_coordinates(app_module.COORDS_FILE)
    r = client.post("/review/0", data={
        "action": "update",
        "latitude": "not-a-number",
        "longitude": "5.0",
        "category": "non_site",
    })
    assert r.status_code == 302
    after = load_coordinates(app_module.COORDS_FILE)
    # Nothing should have changed.
    assert after[0].latitude == before[0].latitude
    assert after[0].category == before[0].category


def test_add_coordinate(client):
    import app as app_module
    r = client.post("/add", data={
        "latitude": "20.0",
        "longitude": "8.0",
        "name": "New",
        "category": "uncertain",
    })
    assert r.status_code == 302
    coords = load_coordinates(app_module.COORDS_FILE)
    assert any(c.name == "New" and c.category == "uncertain" for c in coords)


def test_duplicate_action_appends_copy(client):
    import app as app_module
    before = load_coordinates(app_module.COORDS_FILE)
    r = client.post("/review/0", data={"action": "duplicate"})
    assert r.status_code == 302
    after = load_coordinates(app_module.COORDS_FILE)
    assert len(after) == len(before) + 1
    assert after[-1].category == "uncategorized"
    assert "(copy)" in after[-1].name
