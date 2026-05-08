# sahara-remote-sensing-archaeology

Remote-sensing pipeline for detecting archaeological features in the Sahara — stone structures, tumuli, enclosures, and other surface ruins. Phase 1 is a Flask coordinate-curation tool for building a labeled training set; later phases add satellite image download, augmentation, model training, and wide-area scanning.

## Status

**Phase 1 — coordinate curation (in progress).** A small Flask + Folium app for reviewing GPS coordinates on a satellite map and tagging each as `site`, `non_site`, `uncertain`, or leaving as `uncategorized`.

Current dataset: 993 candidate coordinates across Africa, imported from a Google Saved Places export. ~9% reviewed so far.

## Quick start

Windows (PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Or just double-click [start.bat](start.bat). The app picks a free port in 5000–5100 and opens your browser automatically.

### Importing coordinates

1. Export your Google Maps saved places as JSON (Google Takeout → Saved → GeoJSON).
2. Open the **Import** page in the app and point it at the file.
3. Coordinates outside Africa are filtered out; duplicates (exact lat/lon match) are skipped.

### Reviewing

- Click **Uncategorized** on the index page to start at the first unreviewed coordinate.
- Each review page shows an Esri satellite tile centered on the point. Pick a category, optionally add notes or correct the coordinates, and the app jumps to the next uncategorized one.
- Use **Duplicate** when a single saved point covers multiple distinct features that should be labeled separately.

### Exporting

`GET /export/site` returns a GeoJSON `FeatureCollection` of all confirmed sites — ready for the Phase 2 image-download pipeline.

## Categories

| Category | Meaning |
|---|---|
| `site` | Confirmed archaeological feature (stone structure, tumulus, enclosure, etc.) |
| `non_site` | Not an archaeological feature (natural formation, modern construction, etc.) |
| `uncertain` | Needs better imagery or further research |
| `uncategorized` | Not yet reviewed |

## Roadmap

- **Phase 1** — coordinate curation *(current)*
- **Phase 2** — satellite image download for confirmed sites
- **Phase 3** — data augmentation
- **Phase 4** — model training (likely fine-tuning a pretrained remote-sensing backbone)
- **Phase 5** — wide-area scanning over Sahara tiles

## Project layout

```
app.py                       # Flask routes, single file
src/coordinate_parser.py     # Coordinate dataclass, GeoJSON parsing, atomic save
data/africa_coordinates.json # Live dataset (mutated in place; .bak kept on save)
templates/                   # Jinja templates: index, review, import, add
```

See [CLAUDE.md](CLAUDE.md) for project context and [AGENTS.md](AGENTS.md) for conventions and pitfalls when contributing (or coding-agent assistance).

## Tests

```powershell
venv\Scripts\Activate.ps1
pip install pytest
pytest -v
```

CI runs the same suite on Python 3.10 / 3.11 / 3.12 via [`.github/workflows/ci.yml`](.github/workflows/ci.yml) on every push and PR to `main`.

## License

[MIT](LICENSE).
