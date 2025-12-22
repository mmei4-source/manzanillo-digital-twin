import os
import yaml
import logging
import joblib
import rasterio
import numpy as np
import pandas as pd
import zipfile
from scipy.ndimage import zoom
from datetime import datetime
import sys

# --- FORCE PRINTING TO SCREEN ---
print("DEBUG: Script has started...")

# --- 1. ROBUST PATH SETUP ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
print(f"DEBUG: Project Root detected as: {PROJECT_ROOT}")

# --- 2. SETUP LOGGING ---
log_dir = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(log_dir, f"run_{datetime.now().strftime('%Y%m%d')}.log")

print(f"DEBUG: Logging to {log_filename}")

logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# Force logs to screen as well
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

def load_config():
    config_path = os.path.join(PROJECT_ROOT, "config", "settings.yaml")
    print(f"DEBUG: Loading config from {config_path}")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at: {config_path}")
        
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def get_latest_sentinel(sentinel_dir):
    print(f"DEBUG: Searching for satellites in {sentinel_dir}")
    if not os.path.exists(sentinel_dir):
            raise FileNotFoundError(f"Sentinel directory not found: {sentinel_dir}")

    files = [f for f in os.listdir(sentinel_dir) if f.endswith('.zip')]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(sentinel_dir, x)), reverse=True)
    
    if not files:
        raise FileNotFoundError("No Sentinel .zip files found!")
        
    return os.path.join(sentinel_dir, files[0])

def generate_risk_map():
    logging.info("🚀 STARTING AUTOMATED RISK UPDATE")
    print("DEBUG: Function generate_risk_map started.")
    
    # 1. Load Config
    config = load_config()
    print("DEBUG: Config Loaded.")
    
    # 2. Construct Paths
    model_path = os.path.normpath(os.path.join(PROJECT_ROOT, "models", config['files']['model_file']))
    dem_path = os.path.normpath(os.path.join(SCRIPT_DIR, config['paths']['inegi_dem']))
    sentinel_dir = os.path.normpath(os.path.join(SCRIPT_DIR, config['paths']['sentinel_dir']))
    output_dir = os.path.normpath(os.path.join(SCRIPT_DIR, config['paths']['processed_data']))
    output_file = os.path.join(output_dir, config['files']['risk_map_output'])

    # 3. Load Resources
    logging.info(f"Loading AI Model: {model_path}")
    model = joblib.load(model_path)
    
    logging.info(f"Loading Terrain: {dem_path}")
    # FAST TRACK: Load subsampled DEM
    sample_rate = 5
    with rasterio.open(dem_path) as src:
        dem = src.read(1)[::sample_rate, ::sample_rate]
        # Save CRS for export
        out_crs = src.crs
        out_transform = src.transform * src.transform.scale(sample_rate, sample_rate)
        
        # Calc Slope
        px, py = src.res
        px, py = px * sample_rate, py * sample_rate
        dy, dx = np.gradient(dem, -py, px)
        slope = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))

    # Load Satellite
    sat_path = get_latest_sentinel(sentinel_dir)
    logging.info(f"Using Satellite Image: {os.path.basename(sat_path)}")
    
    with zipfile.ZipFile(sat_path, 'r') as z:
        red_file = [f for f in z.namelist() if "B04" in f and "10m" in f][0]
        nir_file = [f for f in z.namelist() if "B08" in f and "10m" in f][0]
        with rasterio.open(f"/vsizip/{sat_path}/{red_file}") as r: red = r.read(1)
        with rasterio.open(f"/vsizip/{sat_path}/{nir_file}") as n: nir = n.read(1)

    # Resize
    print("DEBUG: Resizing satellite arrays...")
    zoom_y = dem.shape[0] / red.shape[0]
    zoom_x = dem.shape[1] / red.shape[1]
    red_small = zoom(red, (zoom_y, zoom_x), order=0)
    nir_small = zoom(nir, (zoom_y, zoom_x), order=0)
    
    # NDVI
    num = (nir_small - red_small).astype(float)
    den = (nir_small + red_small).astype(float)
    ndvi = np.divide(num, den, out=np.zeros_like(num), where=den!=0)
    
    # Prediction
    logging.info("Running Random Forest Prediction...")
    input_df = pd.DataFrame({
        'Elevation_m': dem.flatten(),
        'Slope_deg': slope.flatten(),
        'NDVI': ndvi.flatten()
    }).fillna(0)
    
    pred = model.predict(input_df)
    biomass_map = pred.reshape(dem.shape)
    
    # Risk
    risk_map = (biomass_map * slope) / (ndvi + 0.2)
    risk_map = np.where(risk_map < 0, 0, risk_map)
    if np.max(risk_map) > 0:
        risk_map = (risk_map / np.max(risk_map)) * 100
        
    # Save
    os.makedirs(output_dir, exist_ok=True)
    print(f"DEBUG: Saving to {output_file}")
    
    with rasterio.open(
        output_file, 'w', driver='GTiff',
        height=risk_map.shape[0], width=risk_map.shape[1],
        count=1, dtype=rasterio.float32,
        crs=out_crs, transform=out_transform
    ) as dst:
        dst.write(risk_map.astype(rasterio.float32), 1)
        
    logging.info("✅ SUCCESS.")

if __name__ == "__main__":
    try:
        generate_risk_map()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        logging.critical(f"❌ SCRIPT FAILED: {e}")
        raise