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

Linux / macOS:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Or use the launchers: double-click [start.bat](start.bat) on Windows, or run [`./start.sh`](start.sh) elsewhere. The app picks a free port in 5000–5100 and opens your browser automatically.

### Running as a persistent server

To keep the app running on a LAN machine and label from any browser on the network:

```bash
SAHARA_HOST=0.0.0.0 SAHARA_PORT=5000 python app.py
```

| Variable | Effect |
|---|---|
| `SAHARA_HOST` | Bind address. Default `127.0.0.1`. Any non-loopback host runs with Flask debug **off** and does not open a browser. |
| `SAHARA_PORT` | Fixed port. Default: first free port in 5000–5100. |
| `SAHARA_NO_BROWSER` | Set to anything to suppress the auto-open browser on loopback. |

The app has no authentication, so only expose it on a trusted network.

### Importing coordinates

1. Export your Google Maps saved places as JSON (Google Takeout → Saved → GeoJSON).
2. Open the **Import** page in the app and point it at the file.
3. Coordinates outside Africa are filtered out; duplicates (exact lat/lon match) are skipped.

### Reviewing

Two views, same data:

**Triage grid** (`/triage`) — fast first pass. Shows 6–48 satellite thumbnails per page, each a small pannable/zoomable Leaflet map centered on the point. Hover a tile and press `1` / `2` / `3` for site / non-site / uncertain (`0` clears), or click the buttons. `Enter` saves the page and loads the next batch; `S` skips a page without saving. Tiles you don't touch keep their current category. The **Open** link on each tile jumps to the full review page for that row.

**Review page** (`/review/<index>`) — one point at a time with a full-size satellite map. Pick a category, set a feature type (tumulus, enclosure, keyhole, …), add notes, correct the coordinates, and the app jumps to the next one in the same category filter. Use **Duplicate** when a single saved point covers multiple distinct features that should be labeled separately.

Suggested workflow: clear obvious negatives and flag candidates in the triage grid, then go through `uncertain` and `site` on the review page to add feature types and notes.

### Exporting

`GET /export/site` returns a GeoJSON `FeatureCollection` of all confirmed sites (with `name`, `notes`, and `site_type` properties) — ready for the Phase 2 image-download pipeline.

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
templates/                   # Jinja templates: index, triage, review, import, add
static/vendor/leaflet/       # Vendored Leaflet 1.9.4 (BSD-2) so the triage grid works offline
start.bat / start.sh         # Launchers for Windows / Linux+macOS
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
