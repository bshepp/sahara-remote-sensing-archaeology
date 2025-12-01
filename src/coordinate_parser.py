"""
Parse Google Saved Places JSON and filter to Africa coordinates.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class Coordinate:
    latitude: float
    longitude: float
    name: str
    address: str
    date_saved: str
    source_url: str
    category: str = "uncategorized"  # ruins, not_ruins, uncertain
    notes: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


# Africa bounding box (approximate)
AFRICA_BOUNDS = {
    "lat_min": -35.0,
    "lat_max": 37.5,
    "lon_min": -25.0,
    "lon_max": 55.0,
}


def is_in_africa(lat: float, lon: float) -> bool:
    """Check if coordinates fall within Africa's bounding box."""
    return (
        AFRICA_BOUNDS["lat_min"] <= lat <= AFRICA_BOUNDS["lat_max"]
        and AFRICA_BOUNDS["lon_min"] <= lon <= AFRICA_BOUNDS["lon_max"]
    )


def extract_coords_from_url(url: str) -> Optional[tuple]:
    """
    Extract coordinates from Google Maps URL.
    Handles formats like:
    - ?q=21.012128,51.250482
    - ?q=17.092299999999998,7.939952
    """
    if not url:
        return None
    
    # Pattern for ?q=lat,lon
    match = re.search(r'\?q=([-\d.]+),([-\d.]+)', url)
    if match:
        try:
            lat = float(match.group(1))
            lon = float(match.group(2))
            return (lat, lon)
        except ValueError:
            pass
    
    return None


def parse_google_places_json(filepath: Path) -> List[Coordinate]:
    """
    Parse Google Saved Places GeoJSON export.
    Returns list of Coordinate objects.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    coordinates = []
    
    for feature in data.get("features", []):
        geometry = feature.get("geometry", {})
        props = feature.get("properties", {})
        
        # GeoJSON uses [longitude, latitude]
        coords = geometry.get("coordinates", [0, 0])
        lon, lat = coords[0], coords[1]
        
        # If coords are 0,0, try to extract from URL
        if lon == 0 and lat == 0:
            url = props.get("google_maps_url", "")
            extracted = extract_coords_from_url(url)
            if extracted:
                lat, lon = extracted
        
        # Skip if still no valid coordinates
        if lon == 0 and lat == 0:
            continue
        
        location = props.get("location", {})
        
        coord = Coordinate(
            latitude=lat,
            longitude=lon,
            name=location.get("name", "Unnamed"),
            address=location.get("address", ""),
            date_saved=props.get("date", ""),
            source_url=props.get("google_maps_url", ""),
        )
        
        coordinates.append(coord)
    
    return coordinates


def filter_africa_coordinates(coordinates: List[Coordinate]) -> List[Coordinate]:
    """Filter coordinates to only those within Africa."""
    return [c for c in coordinates if is_in_africa(c.latitude, c.longitude)]


def save_coordinates(coordinates: List[Coordinate], filepath: Path):
    """Save coordinates to JSON file."""
    data = [c.to_dict() for c in coordinates]
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def load_coordinates(filepath: Path) -> List[Coordinate]:
    """Load coordinates from JSON file."""
    if not filepath.exists():
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return [Coordinate(**item) for item in data]


if __name__ == "__main__":
    # Test parsing
    import sys
    
    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
    else:
        input_file = Path(__file__).parent.parent.parent / "Saved Places.json"
    
    if not input_file.exists():
        print(f"File not found: {input_file}")
        sys.exit(1)
    
    print(f"Parsing {input_file}...")
    all_coords = parse_google_places_json(input_file)
    print(f"Total coordinates: {len(all_coords)}")
    
    africa_coords = filter_africa_coordinates(all_coords)
    print(f"Africa coordinates: {len(africa_coords)}")
    
    # Save to data directory
    output_file = Path(__file__).parent.parent / "data" / "africa_coordinates.json"
    save_coordinates(africa_coords, output_file)
    print(f"Saved to {output_file}")

