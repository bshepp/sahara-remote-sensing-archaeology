# CLAUDE.md

Guidance for working with sahara-sites.

## Project Purpose

Coordinate curation tool for archaeological site detection from satellite imagery. This is Phase 1 - building a clean training dataset of Saharan archaeological sites (stone structures, tumuli, enclosures, etc.).

## Current Status

Phase 1: Coordinate curation (in progress)
- Import Google Saved Places JSON
- Filter to Africa
- Review/categorize each coordinate as site/non-site/uncertain
  - `/triage` grid for fast first-pass labeling, `/review/<i>` for detail + feature type + notes
- Export verified coordinates for training

Known data gaps (as of Nov 2026): ~900 of 993 points still uncategorized; only 6 confirmed sites, all in one cluster near 25N 8E and none with feature types or notes. Expect to need external positive sources (OSM `historic=archaeological_site`, published tumulus surveys) before Phase 4.

Future phases:
- Phase 2: Satellite image download
- Phase 3: Data augmentation
- Phase 4: Model training
- Phase 5: Wide area scanning

## Commands

```bash
# Setup
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Run web app (local; auto-picks a port in 5000-5100, opens browser)
python app.py

# Run as a persistent LAN server (debug off, no browser)
SAHARA_HOST=0.0.0.0 SAHARA_PORT=5000 python app.py

# Run tests
pip install pytest
pytest -v
```

## File Structure

- `app.py` - Flask web application
- `src/coordinate_parser.py` - JSON parsing and filtering; `SITE_TYPES` suggestion list
- `data/africa_coordinates.json` - Curated coordinates
- `templates/` - HTML templates (index, triage, review, import, add)
- `static/vendor/leaflet/` - Vendored Leaflet for the triage grid
- `tests/` - pytest suite (parser + Flask routes)
- `.github/workflows/ci.yml` - CI on Python 3.10/3.11/3.12

## Categories

- **site** - Confirmed archaeological feature (stone structure, tumulus, enclosure, etc.)
- **non_site** - Not an archaeological feature (natural formation, modern, etc.)
- **uncertain** - Needs more research or better imagery
- **uncategorized** - Not yet reviewed

Sites also carry an optional free-text `site_type` (tumulus, cairn, keyhole, crescent, enclosure, stone circle, wall, structure, field system, other).

## Data Flow

1. Import: Google Saved Places JSON → filter to Africa → store
2. Review: View each coordinate on satellite map, categorize
3. Export: Get GeoJSON of verified "site" coordinates for training
