# AGENTS.md

Guidance for AI coding agents working in **sahara-sites** (a.k.a. ruins-finder).

See [CLAUDE.md](CLAUDE.md) for project purpose, phases, and category definitions — that doc is canonical and should not be duplicated here.

## Run / dev loop

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
python app.py            # auto-picks free port 5000–5100, opens browser
```

Linux/macOS: `source venv/bin/activate && python app.py`, or `./start.sh`. For a headless check use `SAHARA_HOST=127.0.0.1 SAHARA_PORT=5077 SAHARA_NO_BROWSER=1 python app.py` and drive it with the Playwright that ships in the cloud sandbox. There is no linter or build step; UI changes still need browser verification.

Env vars (read in `app.py`'s `__main__` only): `SAHARA_HOST` (non-loopback forces `debug=False`), `SAHARA_PORT`, `SAHARA_NO_BROWSER`.

## Tests

```powershell
pip install pytest
pytest -v
```

Tests live in [tests/](tests) and cover the parser ([tests/test_coordinate_parser.py](tests/test_coordinate_parser.py)) and Flask routes ([tests/test_app.py](tests/test_app.py)). The `client` fixture in [tests/conftest.py](tests/conftest.py) monkeypatches `app.COORDS_FILE` to a temp dir, so tests never mutate [data/africa_coordinates.json](data/africa_coordinates.json) — preserve that pattern when adding tests. CI runs the same suite on Python 3.10 / 3.11 / 3.12 via [.github/workflows/ci.yml](.github/workflows/ci.yml).

Standalone parser smoke test:

```powershell
python src\coordinate_parser.py "path\to\Saved Places.json"
```

## Architecture (small, deliberate)

- [app.py](app.py) — single-file Flask app. All routes live here. Loads/saves the full coordinate list from disk on every request (fine at this scale; do not add a DB or caching layer unless asked).
- [src/coordinate_parser.py](src/coordinate_parser.py) — pure data layer: `Coordinate` dataclass, Google Places GeoJSON parsing, Africa bbox filter, JSON load/save. No Flask imports here — keep it that way.
- [data/africa_coordinates.json](data/africa_coordinates.json) — the live dataset, mutated in place by the app. Treat as user data: never overwrite or reorder without an explicit request.
- [templates/](templates) — Jinja templates (`index`, `triage`, `review`, `import`, `add`). `index` and `review` render maps server-side via Folium and embed raw HTML (`m._repr_html_()`). `triage` is different: it renders many small Leaflet maps client-side from the vendored copy in [static/vendor/leaflet/](static/vendor/leaflet) — no Folium, so it works offline and loads fast with 48 tiles.
- `/triage` POST writes only the `cat_<index>` fields whose value differs from what is stored, and ignores unknown indices / category strings. Keep that contract; it is what makes a half-filled page safe to submit.

## Conventions specific to this codebase

- **Indexing is positional.** Routes like `/review/<int:index>` and the "next in category" navigation rely on the list order in `africa_coordinates.json`. Do not sort or dedupe the list as a side effect of unrelated changes.
- **Categories are string literals**, not enums: `site`, `non_site`, `uncertain`, `uncategorized`. Match exactly; the UI color map and filters depend on these strings.
- **GeoJSON order is `[lon, lat]`** (see `parse_google_places_json` and `/export/<category>`). Internal `Coordinate` stores `latitude, longitude` — easy place to introduce bugs.
- **Coordinate dedupe key** when importing is `(latitude, longitude)` exact match — see `import_data` in [app.py](app.py). Don't change this without considering existing data.
- **Satellite tiles** use Esri World_Imagery on the review page; the index map uses default OSM with a `MarkerCluster`. Keep this split — reviewers need satellite, the overview needs clustering.
- Adding a coordinate field requires updating: the `Coordinate` dataclass, `parse_google_places_json`, the review template form, and the `review` POST handler. `to_dict`/`load_coordinates` use `asdict` / `**item` so they pick up new fields automatically — but old JSON rows will fail `Coordinate(**item)` unless the field has a default. `site_type` (added after the initial data import) is the worked example: it defaults to `""`, so the live JSON only gains the key on the next save.
- `site_type` is free text with a `<datalist>` of suggestions from `SITE_TYPES` in the parser module. Add new suggested types there, not in the template.

## Pitfalls

- The app runs with `debug=True, use_reloader=False`. Don't enable the reloader — it double-opens the browser and can double-write data on POST.
- `find_available_port` only checks 5000–5100; templates and any hardcoded URLs should stay relative.
- Phase 1 only: do **not** add satellite-image download, ML, or scanning code unless the user explicitly moves to Phase 2+.
