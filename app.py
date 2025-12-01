"""
Flask web app for reviewing and curating archaeological site coordinates.
"""

import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for
import folium
from folium.plugins import MarkerCluster

from src.coordinate_parser import (
    Coordinate,
    load_coordinates,
    save_coordinates,
    parse_google_places_json,
    filter_africa_coordinates,
)

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
            # Update coordinate
            coord.category = request.form.get('category', coord.category)
            coord.notes = request.form.get('notes', coord.notes)
            
            # Allow coordinate correction
            try:
                new_lat = float(request.form.get('latitude', coord.latitude))
                new_lon = float(request.form.get('longitude', coord.longitude))
                coord.latitude = new_lat
                coord.longitude = new_lon
            except ValueError:
                pass
            
            coord.name = request.form.get('name', coord.name)
            coords[index] = coord
            save_all_coordinates(coords)
            
            # Go to next uncategorized
            next_idx = find_next_uncategorized(coords, index)
            if next_idx is not None:
                return redirect(url_for('review', index=next_idx))
            return redirect(url_for('index'))
        
        elif action == 'delete':
            coords.pop(index)
            save_all_coordinates(coords)
            return redirect(url_for('index'))
        
        elif action == 'skip':
            next_idx = find_next_uncategorized(coords, index)
            if next_idx is not None:
                return redirect(url_for('review', index=next_idx))
            return redirect(url_for('index'))
    
    # Generate focused map
    m = folium.Map(location=[coord.latitude, coord.longitude], zoom_start=15)
    
    # Add satellite tile layer
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
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
    uncategorized_count = len([c for c in coords if c.category == 'uncategorized'])
    
    return render_template('review.html', 
        coord=coord, 
        index=index, 
        total=total,
        uncategorized_count=uncategorized_count,
        map_html=map_html,
        prev_index=index - 1 if index > 0 else None,
        next_index=index + 1 if index < total - 1 else None,
    )


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
                }
            }
            for c in filtered
        ]
    }
    
    return jsonify(output)


def find_next_uncategorized(coords: list, current_index: int) -> int:
    """Find the next uncategorized coordinate after current index."""
    for i in range(current_index + 1, len(coords)):
        if coords[i].category == 'uncategorized':
            return i
    # Wrap around
    for i in range(0, current_index):
        if coords[i].category == 'uncategorized':
            return i
    return None


if __name__ == '__main__':
    DATA_DIR.mkdir(exist_ok=True)
    app.run(debug=True, port=5000)

