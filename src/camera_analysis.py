import rasterio
import numpy as np
import matplotlib.pyplot as plt
import os
import json

# --- 1. ROBUST PATH SETUP ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Paths to resources
RISK_MAP = os.path.join(PROJECT_ROOT, "data/processed/daily_fire_risk_map.tif")
OUTPUT_IMG = os.path.join(PROJECT_ROOT, "data/processed/camera_gap_analysis.png")

def simple_viewshed(dem, cam_r, cam_c, radius_pixels=150):
    """
    Simulates 'Line of Sight'. 
    (Simplified for Pilot: assumes if pixel is lower & close, we see it).
    """
    rows, cols = dem.shape
    visible_map = np.zeros_like(dem, dtype=bool)
    
    # Define the square box around the camera
    r_min = max(0, cam_r - radius_pixels)
    r_max = min(rows, cam_r + radius_pixels)
    c_min = max(0, cam_c - radius_pixels)
    c_max = min(cols, cam_c + radius_pixels)
    
    # Get Camera Height (Terrain + 15m Pole)
    cam_height = dem[cam_r, cam_c] + 15 
    
    # Extract the local patch of terrain
    local_dem = dem[r_min:r_max, c_min:c_max]
    
    # LOGIC: A pixel is visible if it is LOWER than the camera height
    # (In a real deployment, we would use ray-tracing, but this is fast for a Pilot)
    visible_patch = local_dem < cam_height
    
    # Add to master map
    visible_map[r_min:r_max, c_min:c_max] = visible_patch
    return visible_map

def analyze_cameras():
    print("🚀 STARTING CAMERA NETWORK ANALYSIS")
    
    # 1. Load the 'War Map' (Risk Map)
    # We use this to find where the 'Enemy' (Fire) is hiding
    if not os.path.exists(RISK_MAP):
        print(f"❌ ERROR: Risk map not found at {RISK_MAP}")
        return

    with rasterio.open(RISK_MAP) as src:
        risk_data = src.read(1)
        # Also load Elevation for Line-of-Sight calculation
        # (For this pilot, we treat Risk Score ~ Elevation proxy for visual clarity,
        # but normally we'd load the DEM separately. We will use Risk Data 
        # as a placeholder for terrain roughness here to keep it simple).
        transform = src.transform

    # 2. Simulate Existing Public Cameras
    # We place these in downtown Manzanillo (Low risk area)
    cameras = [
        {"id": "Downtown_1", "lat": 19.050, "lon": -104.310}, 
        {"id": "Port_Gate_2", "lat": 19.060, "lon": -104.300}, 
        {"id": "Hwy_Entrance", "lat": 19.090, "lon": -104.280}, 
    ]
    
    print(f"   Simulating {len(cameras)} existing public cameras...")
    
    # 3. Calculate Vision Coverage
    total_coverage = np.zeros_like(risk_data, dtype=bool)
    
    for cam in cameras:
        # Find pixel coordinates
        try:
            row, col = rasterio.transform.rowcol(transform, cam['lon'], cam['lat'])
            # Check if inside map
            if 0 <= row < risk_data.shape[0] and 0 <= col < risk_data.shape[1]:
                # Calculate View
                viewshed = simple_viewshed(risk_data, row, col)
                total_coverage = np.logical_or(total_coverage, viewshed)
                print(f"   ✅ Camera {cam['id']} is online.")
            else:
                print(f"   ⚠️ Camera {cam['id']} is outside the map area.")
        except Exception as e:
            print(f"   ⚠️ Error placing camera: {e}")

    # 4. IDENTIFY BLIND SPOTS (The Strategic Gap)
    # A Blind Spot is where Risk is High (>50) BUT Coverage is Zero.
    high_risk_zone = risk_data > 50
    blind_spots = np.logical_and(high_risk_zone, ~total_coverage)
    
    blind_pixel_count = np.sum(blind_spots)
    print(f"\n   ⚠️ ANALYSIS COMPLETE: {blind_pixel_count} High-Risk pixels are INVISIBLE.")

    # 5. PLOT THE EVIDENCE
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # A. Background: The Risk Map (Grey/Black)
    ax.imshow(risk_data, cmap='Greys', alpha=0.5)
    
    # B. The Existing Safety Net (Blue)
    # This represents the current public camera system
    coverage_plot = np.ma.masked_where(~total_coverage, total_coverage)
    ax.imshow(coverage_plot, cmap='Blues', alpha=0.5, label='Current Camera Coverage')
    
    # C. The Blind Spots (Red)
    # This represents the danger zones that need NEW Tech (AI Cameras)
    blind_plot = np.ma.masked_where(~blind_spots, blind_spots)
    ax.imshow(blind_plot, cmap='Reds', label='UNMONITORED HIGH RISK')
    
    ax.set_title("GAP ANALYSIS: Why Manzanillo Needs AI Cameras\n(Red = High Risk + No Visibility)")
    ax.axis('off')
    
    plt.savefig(OUTPUT_IMG)
    print(f"✅ Evidence Map Saved to: {OUTPUT_IMG}")

if __name__ == "__main__":
    analyze_cameras()