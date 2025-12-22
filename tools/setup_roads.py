import osmnx as ox
import os

def download_manzanillo_roads():
    """
    Acquires the exact drivable road network for the Port of Manzanillo
    and saves it as a reusable GraphML file.
    
    COMPATIBILITY: Updated for OSMnx v2.0+
    """
    print("🌐 Connecting to OpenStreetMap Overpass API...")
    
    # 1. Define the Bounding Box (Manzanillo Port & Surrounding Area)
    # Matches your zones.json BBOX roughly, but slightly larger for logistics routing
    north, south = 19.18, 19.00
    east, west = -104.15, -104.40
    
    print(f"📍 Downloading Drive Network for BBOX: N{north}, S{south}, E{east}, W{west}")
    
    try:
        # Download 'drive' network (excludes walking paths)
        # UPDATED SYNTAX: OSMnx 2.0 requires 'bbox' as a tuple (north, south, east, west)
        G = ox.graph_from_bbox(bbox=(north, south, east, west), network_type='drive')
        
        # Project to UTM (Meters) for accurate distance calculations
        G_proj = ox.project_graph(G)
        
        # 2. Setup Paths
        # We save this in data/processed so the main app can load it fast
        # Go up one level from 'tools' to project root
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "data", "processed")
        os.makedirs(data_dir, exist_ok=True)
        
        save_path = os.path.join(data_dir, "manzanillo_drive.graphml")
        
        # 3. Save
        ox.save_graphml(G_proj, save_path)
        print(f"✅ SUCCESS: Road network saved to {save_path}")
        # Note: In V2, stats are calculated differently, skipping print stats to avoid further version conflicts
        print("   Ready for Logistics Engine.")
        
    except Exception as e:
        print(f"❌ CRITICAL FAILURE: Could not download road data. {e}")

if __name__ == "__main__":
    download_manzanillo_roads()