import json
import os

# --- CONFIGURATION ---
# We define the "Boxes" using Latitude/Longitude
# (Approximate coordinates based on Manzanillo geography)

ZONES = {
    "ZONE_A_CURRENT_PORT": {
        "description": "The operating port, downtown, and main logistics corridor.",
        "bbox": {
            "min_lat": 19.030,
            "max_lat": 19.100,
            "min_lon": -104.350,
            "max_lon": -104.280
        },
        "priority": "Asset Protection",
        "technologies": ["Grid_Sensors", "CCTV_Smoke_Detection", "Smart_Panels"]
    },
    "ZONE_B_EXPANSION": {
        "description": "Laguna de Cuyutlán and the Northern Expansion area.",
        "bbox": {
            "min_lat": 19.100,
            "max_lat": 19.180,
            "min_lon": -104.300,
            "max_lon": -104.150
        },
        "priority": "Ecological Stability & Construction Safety",
        "technologies": ["IoT_Gas_Mesh", "Vegetation_Analysis", "Drone_Patrols"]
    }
}

def save_zone_config():
    # Find the 'config' folder relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    config_path = os.path.join(project_root, "config", "zones.json")
    
    with open(config_path, "w") as f:
        json.dump(ZONES, f, indent=4)
        
    print(f"✅ ZONE CONFIGURATION SAVED TO: {config_path}")
    print("   System now recognizes 'Current Port' vs 'Expansion Area'.")

if __name__ == "__main__":
    save_zone_config()