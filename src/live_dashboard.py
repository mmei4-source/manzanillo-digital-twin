import cv2
import numpy as np
import requests
import time
import os
import rasterio
from datetime import datetime
import math
from io import BytesIO
from PIL import Image

# --- CONFIGURATION ---
LAT = 19.052
LON = -104.315
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RISK_MAP_PATH = os.path.join(PROJECT_ROOT, "data/processed/daily_fire_risk_map.tif")

# STRATEGIC VIEW URL (Esri World Imagery - Manzanillo Port Terminals)
SAT_URL = "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export?bbox=-104.32,19.04,-104.28,19.07&bboxSR=4326&size=600,450&format=jpg&f=image"

def get_live_weather():
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m&wind_speed_unit=kn"
        response = requests.get(url, timeout=2)
        return response.json()['current']
    except:
        return None

def get_satellite_view():
    """Downloads the Static Strategic View from Esri."""
    try:
        response = requests.get(SAT_URL, timeout=10)
        if response.status_code == 200:
            # Convert bytes to numpy array for OpenCV
            image = np.asarray(bytearray(response.content), dtype="uint8")
            img = cv2.imdecode(image, cv2.IMREAD_COLOR)
            return img
        else:
            return None
    except Exception as e:
        print(f"Satellite Download Error: {e}")
        return None

def load_risk_map():
    if not os.path.exists(RISK_MAP_PATH):
        # Create placeholder if map missing
        return np.zeros((500, 500, 3), dtype=np.uint8)
    with rasterio.open(RISK_MAP_PATH) as src:
        img = src.read(1)
        img_norm = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
        img_color = cv2.applyColorMap(img_norm.astype(np.uint8), cv2.COLORMAP_INFERNO)
        return img_color

def draw_compass(img, wind_deg, wind_speed, x, y, size=40):
    # Dial
    cv2.circle(img, (x, y), size, (100, 100, 100), 2)
    cv2.circle(img, (x, y), 2, (0, 255, 255), -1) 
    
    # Arrow
    angle_rad = math.radians(wind_deg - 90) 
    end_x = int(x + size * 0.8 * math.cos(angle_rad))
    end_y = int(y + size * 0.8 * math.sin(angle_rad))
    
    cv2.arrowedLine(img, (x, y), (end_x, end_y), (0, 255, 255), 2, tipLength=0.3)
    
    # Labels
    cv2.putText(img, "N", (x-5, y-size-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    cv2.putText(img, f"{wind_speed} kn", (x-20, y+size+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

def create_dashboard():
    print("🚀 LAUNCHING STRATEGIC COMMAND DASHBOARD...")
    print("   Press 'q' or click 'X' to exit.")

    # 1. Load Static Assets (Risk Map)
    risk_map_img = load_risk_map()
    
    # 2. Load Strategic View (Satellite)
    # Instead of a webcam, we fetch the satellite image once
    print("   Fetching Satellite Recon...")
    sat_view = get_satellite_view()
    if sat_view is None:
        # Fallback if offline
        sat_view = np.zeros((300, 400, 3), dtype=np.uint8)
        cv2.putText(sat_view, "SAT LINK OFFLINE", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

    # Layout Math
    target_h = 600
    scale = target_h / risk_map_img.shape[0]
    target_w = int(risk_map_img.shape[1] * scale)
    risk_map_resized = cv2.resize(risk_map_img, (target_w, target_h))
    
    window_name = 'Manzanillo Resilience Command'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    last_weather_update = 0
    wx = None
    frame_count = 0

    while True:
        # Pulse Check
        try:
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
        except:
            break

        # 3. Update Weather (Every 10s)
        now = time.time()
        if now - last_weather_update > 10:
            new_data = get_live_weather()
            if new_data:
                wx = new_data
                last_weather_update = now
        
        # 4. Info Panel
        info_panel = np.zeros((300, 400, 3), dtype=np.uint8)
        info_panel[:] = (40, 40, 40) 
        
        if wx:
            cv2.putText(info_panel, "LIVE TELEMETRY", (20, 30), cv2.FONT_HERSHEY_TRIPLEX, 0.7, (255, 255, 255), 1)
            cv2.putText(info_panel, f"Temp: {wx['temperature_2m']} C", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(info_panel, f"Hum:  {wx['relative_humidity_2m']} %", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            draw_compass(info_panel, wx['wind_direction_10m'], wx['wind_speed_10m'], 300, 150, size=50)
            cv2.putText(info_panel, "WIND VECTOR", (250, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            # Timers
            age = int(now - last_weather_update)
            cv2.putText(info_panel, f"Data Age: {age}s", (20, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Heartbeat
        frame_count += 1
        if (frame_count % 20) < 10:
            cv2.circle(info_panel, (380, 20), 5, (0, 255, 0), -1)

        # 5. Stitch Layout
        # Top Right: Satellite | Bottom Right: Weather
        # Resize Satellite to fit the sidebar width (400px)
        sat_resized = cv2.resize(sat_view, (400, 300))
        
        sidebar = np.vstack((sat_resized, info_panel))
        
        # Final Stitch
        if sidebar.shape[0] != target_h:
            sidebar = cv2.resize(sidebar, (400, target_h))
            
        dashboard = np.hstack((risk_map_resized, sidebar))
        
        # Add Labels
        cv2.putText(dashboard, "RISK HEATMAP (AI)", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(dashboard, "STRATEGIC VIEW (SAT)", (target_w + 20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        cv2.imshow(window_name, dashboard)

        if cv2.waitKey(50) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()
    print("✅ Dashboard Closed.")

if __name__ == "__main__":
    create_dashboard()