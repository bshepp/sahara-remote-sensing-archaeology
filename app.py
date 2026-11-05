"""
Flask web app for reviewing and curating archaeological site coordinates.
"""

import json
import os
from pathlib import Path
from typing import Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import folium
from folium.plugins import MarkerCluster

from src.coordinate_parser import (
    Coordinate,
    SITE_TYPES,
    load_coordinates,
    save_coordinates,
    parse_google_places_json,
    filter_africa_coordinates,
)

CATEGORIES = ('site', 'non_site', 'uncertain', 'uncategorized')
ESRI_TILES = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'sahara-sites-dev-key'

DATA_DIR = Path(__file__).parent / "data"
COORDS_FILE = DATA_DIR / "africa_coordinates.json"


def get_coordinates() -> list:
    """Load current coordinates."""
    return load_coordinates(COORDS_FILE)


def save_all_coordinates(coords: list):
    """Save coordinates to file."""
    DATA_DIR.mkdir(exist_ok=True)
    save_coordinates(coords, COORDS_FILE)


@app.route('/')
def index():
    """Main page with map and coordinate list."""
    coords = get_coordinates()
    
    # Stats
    stats = {
        'total': len(coords),
        'site': len([c for c in coords if c.category == 'site']),
        'non_site': len([c for c in coords if c.category == 'non_site']),
        'uncertain': len([c for c in coords if c.category == 'uncertain']),
        'uncategorized': len([c for c in coords if c.category == 'uncategorized']),
    }
    
    # Check for filter
    filter_category = request.args.get('filter')
    
    # Generate map
    if coords:
        center_lat = sum(c.latitude for c in coords) / len(coords)
        center_lon = sum(c.longitude for c in coords) / len(coords)
        m = folium.Map(location=[center_lat, center_lon], zoom_start=5)
    else:
        # Default to Sahara region
        m = folium.Map(location=[23.0, 5.0], zoom_start=4)
    
    marker_cluster = MarkerCluster().add_to(m)
    
    for i, coord in enumerate(coords):
        # Color by category
        colors = {
            'site': 'green',
            'non_site': 'red',
            'uncertain': 'orange',
            'uncategorized': 'blue',
        }
        color = colors.get(coord.category, 'blue')
        
        popup_html = f"""
        <div style="min-width:200px">
            <b>{coord.name}</b><br>
            <small>{coord.address}</small><br>
            <hr>
            Lat: {coord.latitude:.6f}<br>
            Lon: {coord.longitude:.6f}<br>
            Category: <b>{coord.category}</b><br>
            <hr>
            <a href="/review/{i}">Review this site</a>
        </div>
        """
        
        folium.Marker(
            location=[coord.latitude, coord.longitude],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=color),
        ).add_to(marker_cluster)
    
    map_html = m._repr_html_()
    
    return render_template('index.html', stats=stats, map_html=map_html, coords=coords)


@app.route('/import', methods=['GET', 'POST'])
def import_data():
    """Import from Google Saved Places JSON."""
    if request.method == 'POST':
        source_file = Path(request.form.get('filepath', ''))
        
        if not source_file.exists():
            return render_template('import.html', error=f"File not found: {source_file}")
        
        try:
            all_coords = parse_google_places_json(source_file)
            africa_coords = filter_africa_coordinates(all_coords)
            
            # Merge with existing
            existing = get_coordinates()
            existing_keys = {(c.latitude, c.longitude) for c in existing}
            
            new_coords = [c for c in africa_coords if (c.latitude, c.longitude) not in existing_keys]
            merged = existing + new_coords
            
            save_all_coordinates(merged)
            
            return render_template('import.html', 
                success=f"Imported {len(new_coords)} new coordinates ({len(all_coords)} total in file, {len(africa_coords)} in Africa)")
        except Exception as e:
            return render_template('import.html', error=str(e))
    
    return render_template('import.html')


@app.route('/review/<int:index>', methods=['GET', 'POST'])
def review(index: int):
    """Review a single coordinate."""
    coords = get_coordinates()
    
    if index < 0 or index >= len(coords):
        return redirect(url_for('index'))
    
    coord = coords[index]
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update':
            # Validate coordinate edits BEFORE applying any other changes,
            # so a typo can't cause a partial save with a misleading success.
            lat_raw = request.form.get('latitude', str(coord.latitude))
            lon_raw = request.form.get('longitude', str(coord.longitude))
            try:
                new_lat = float(lat_raw)
                new_lon = float(lon_raw)
            except ValueError:
                flash(f"Invalid coordinates: lat={lat_raw!r}, lon={lon_raw!r}. Nothing saved.", 'error')
                return redirect(url_for('review', index=index,
                                        filter_category=request.form.get('filter_category', 'uncategorized')))

            coord.latitude = new_lat
            coord.longitude = new_lon
            coord.category = request.form.get('category', coord.category)
            coord.notes = request.form.get('notes', coord.notes)
            coord.site_type = request.form.get('site_type', coord.site_type).strip()
            coord.name = request.form.get('name', coord.name)
            coords[index] = coord
            save_all_coordinates(coords)

            # Go to next in filter category (or uncategorized by default)
            filter_cat = request.form.get('filter_category', 'uncategorized')
            next_idx = find_next_in_category(coords, index, filter_cat)
            if next_idx is not None:
                return redirect(url_for('review', index=next_idx, filter_category=filter_cat))
            return redirect(url_for('index'))
        
        elif action == 'delete':
            coords.pop(index)
            save_all_coordinates(coords)
            return redirect(url_for('index'))
        
        elif action == 'skip':
            filter_cat = request.form.get('filter_category')
            next_idx = find_next_in_category(coords, index, filter_cat or 'uncategorized')
            if next_idx is not None:
                return redirect(url_for('review', index=next_idx, filter_category=filter_cat))
            return redirect(url_for('index'))
        
        elif action == 'duplicate':
            # Create a copy of this coordinate for splitting multiple objects
            new_coord = Coordinate(
                latitude=coord.latitude,
                longitude=coord.longitude,
                name=f"{coord.name} (copy)",
                address=coord.address,
                date_saved=coord.date_saved,
                source_url=coord.source_url,
                category='uncategorized',
                notes=f"Split from: {coord.name}",
            )
            coords.append(new_coord)
            save_all_coordinates(coords)
            # Go to the new coordinate
            return redirect(url_for('review', index=len(coords) - 1))
    
    # Generate focused map
    m = folium.Map(location=[coord.latitude, coord.longitude], zoom_start=15)
    
    # Add satellite tile layer
    folium.TileLayer(
        tiles=ESRI_TILES,
        attr='Esri',
        name='Satellite',
    ).add_to(m)
    
    folium.Marker(
        location=[coord.latitude, coord.longitude],
        icon=folium.Icon(color='red', icon='info-sign'),
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    map_html = m._repr_html_()
    
    # Navigation info
    total = len(coords)
    filter_category = request.args.get('filter_category', 'uncategorized')
    filtered_count = len([c for c in coords if c.category == filter_category])
    
    return render_template('review.html', 
        coord=coord, 
        index=index, 
        total=total,
        filtered_count=filtered_count,
        filter_category=filter_category,
        map_html=map_html,
        site_types=SITE_TYPES,
        prev_index=index - 1 if index > 0 else None,
        next_index=index + 1 if index < total - 1 else None,
    )


@app.route('/triage', methods=['GET', 'POST'])
def triage():
    """Grid view: label many coordinates per page from satellite thumbnails.

    GET  /triage?category=uncategorized&offset=0&per_page=12&zoom=16
    POST form fields `cat_<index>` (one per tile, value in CATEGORIES) plus
         `offset`, `per_page`, `zoom`, `category`. Only tiles whose value
         differs from the stored category are written.

    Indices are positions in the full list (same as /review/<index>), so a
    tile's "Open" link lands on the full review page for that row.
    """
    coords = get_coordinates()

    if request.method == 'POST':
        changed = 0
        for key, value in request.form.items():
            if not key.startswith('cat_'):
                continue
            try:
                idx = int(key[4:])
            except ValueError:
                continue
            if idx < 0 or idx >= len(coords) or value not in CATEGORIES:
                continue
            if coords[idx].category != value:
                coords[idx].category = value
                changed += 1
        if changed:
            save_all_coordinates(coords)
            flash(f"Saved {changed} label{'s' if changed != 1 else ''}.", 'info')

        # The filtered list shrinks as rows get labeled, so keep the same
        # offset unless the user explicitly skipped the page.
        offset = _int_arg(request.form, 'offset', 0)
        if request.form.get('action') == 'skip':
            offset += _int_arg(request.form, 'per_page', 12)
        return redirect(url_for(
            'triage',
            category=request.form.get('category', 'uncategorized'),
            offset=offset,
            per_page=request.form.get('per_page', 12),
            zoom=request.form.get('zoom', 16),
        ))

    category = request.args.get('category', 'uncategorized')
    if category not in CATEGORIES:
        category = 'uncategorized'
    per_page = max(1, min(48, _int_arg(request.args, 'per_page', 12)))
    zoom = max(12, min(19, _int_arg(request.args, 'zoom', 16)))

    matching = [(i, c) for i, c in enumerate(coords) if c.category == category]
    offset = max(0, min(_int_arg(request.args, 'offset', 0), max(len(matching) - 1, 0)))
    page = matching[offset:offset + per_page]

    return render_template(
        'triage.html',
        tiles=page,
        category=category,
        categories=CATEGORIES,
        offset=offset,
        per_page=per_page,
        zoom=zoom,
        remaining=len(matching),
        total=len(coords),
        tile_url=ESRI_TILES,
        has_prev=offset > 0,
        has_next=offset + per_page < len(matching),
    )


def _int_arg(source, key: str, default: int) -> int:
    """Parse an int from a request dict, falling back to default on junk."""
    try:
        return int(source.get(key, default))
    except (TypeError, ValueError):
        return default


@app.route('/add', methods=['GET', 'POST'])
def add_coordinate():
    """Add a new coordinate manually."""
    if request.method == 'POST':
        try:
            coord = Coordinate(
                latitude=float(request.form['latitude']),
                longitude=float(request.form['longitude']),
                name=request.form.get('name', 'Manual entry'),
                address=request.form.get('address', ''),
                date_saved='',
                source_url='',
                category=request.form.get('category', 'uncategorized'),
                notes=request.form.get('notes', ''),
            )
            
            coords = get_coordinates()
            coords.append(coord)
            save_all_coordinates(coords)
            
            return redirect(url_for('index'))
        except ValueError as e:
            return render_template('add.html', error=f"Invalid coordinates: {e}")
    
    return render_template('add.html')


@app.route('/filter/<category>')
def filter_by_category(category: str):
    """Show only coordinates of a specific category, link to first one for review."""
    coords = get_coordinates()
    
    # Find first coordinate of this category
    for i, coord in enumerate(coords):
        if coord.category == category:
            return redirect(url_for('review', index=i, filter_category=category))
    
    # None found
    return redirect(url_for('index'))


@app.route('/api/coordinates')
def api_coordinates():
    """API endpoint for coordinate data."""
    coords = get_coordinates()
    category = request.args.get('category')
    
    if category:
        coords = [c for c in coords if c.category == category]
    
    return jsonify([c.to_dict() for c in coords])


@app.route('/export/<category>')
def export_category(category: str):
    """Export coordinates of a specific category."""
    coords = get_coordinates()
    filtered = [c for c in coords if c.category == category]
    
    output = {
        'type': 'FeatureCollection',
        'features': [
            {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [c.longitude, c.latitude]
                },
                'properties': {
                    'name': c.name,
                    'notes': c.notes,
                    'site_type': c.site_type,
                }
            }
            for c in filtered
        ]
    }
    
    return jsonify(output)


def find_next_in_category(coords: list, current_index: int, category: str = 'uncategorized') -> Optional[int]:
    """Find the next coordinate of given category after current index, or None."""
    for i in range(current_index + 1, len(coords)):
        if coords[i].category == category:
            return i
    # Wrap around
    for i in range(0, current_index):
        if coords[i].category == category:
            return i
    return None


def find_available_port(start=5000, end=5100, host='127.0.0.1'):
    """Find an available port in the given range."""
    import socket
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                return port
        except OSError:
            continue
    return start  # fallback


if __name__ == '__main__':
    import webbrowser
    import threading

    DATA_DIR.mkdir(exist_ok=True)

    # Local desktop use (default): bind loopback, pick a free port, open browser.
    # Persistent LAN server: SAHARA_HOST=0.0.0.0 SAHARA_PORT=5000 python app.py
    # Non-loopback hosts run with debug off so the Werkzeug debugger is never
    # reachable from other machines.
    host = os.environ.get('SAHARA_HOST', '127.0.0.1')
    is_local = host in ('127.0.0.1', 'localhost')
    port_env = os.environ.get('SAHARA_PORT')
    port = int(port_env) if port_env else find_available_port(host=host)
    url = f'http://{host}:{port}'

    print(f'\n  Sahara Sites running at: {url}\n')

    if is_local and not os.environ.get('SAHARA_NO_BROWSER'):
        # Open browser after short delay (gives server time to start)
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    app.run(host=host, debug=is_local, port=port, use_reloader=False)

