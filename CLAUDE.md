# CLAUDE.md

Guidance for working with sahara-sites.

## Project Purpose

Coordinate curation tool for archaeological site detection from satellite imagery. This is Phase 1 - building a clean training dataset of Saharan archaeological sites (stone structures, tumuli, enclosures, etc.).

## Current Status

Phase 1: Coordinate curation (in progress)
- Import Google Saved Places JSON
- Filter to Africa
- Review/categorize each coordinate as site/non-site/uncertain
- Export verified coordinates for training

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

# Run web app
python app.py
# Opens at http://localhost:5000

# Run tests
pip install pytest
pytest -v
```

## File Structure

- `app.py` - Flask web application
- `src/coordinate_parser.py` - JSON parsing and filtering
- `data/africa_coordinates.json` - Curated coordinates
- `templates/` - HTML templates
- `tests/` - pytest suite (parser + Flask routes)
- `.github/workflows/ci.yml` - CI on Python 3.10/3.11/3.12

## Categories

- **site** - Confirmed archaeological feature (stone structure, tumulus, enclosure, etc.)
- **non_site** - Not an archaeological feature (natural formation, modern, etc.)
- **uncertain** - Needs more research or better imagery
- **uncategorized** - Not yet reviewed

## Data Flow

1. Import: Google Saved Places JSON → filter to Africa → store
2. Review: View each coordinate on satellite map, categorize
3. Export: Get GeoJSON of verified "site" coordinates for training
