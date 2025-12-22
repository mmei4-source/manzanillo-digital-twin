import streamlit as st
import folium
from folium.plugins import MousePosition
from streamlit_folium import st_folium
import numpy as np
import rasterio
import requests
import os
import base64
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))
RISK_MAP_PATH = os.path.join(PROJECT_ROOT, "data/processed/daily_fire_risk_map.tif")
ESRI_BASE_URL = "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export"

st.set_page_config(page_title="Real-Time Risk", page_icon="📡", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { min-width: 160px !important; max-width: 160px !important; }
    .hud-box {
        display: flex; align-items: center; background-color: #f8f9fa;
        border: 1px solid #ddd; border-radius: 8px; padding: 5px 15px;
        width: fit-content; margin-bottom: 10px; gap: 20px;
    }
    .hud-metric { display: flex; flex-direction: column; }
    .hud-label { font-size: 0.65rem; color: #666; font-weight: 700; margin-bottom: -3px; }
    .hud-value { font-size: 1.1rem; font-weight: 800; color: #222; font-family: monospace; }
    .compass-img { height: 50px; width: 50px; margin-left: 5px; }
    .block-container { padding: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# --- STATE INITIALIZATION ---
if 'lat_input' not in st.session_state: st.session_state['lat_input'] = 19.060
if 'lon_input' not in st.session_state: st.session_state['lon_input'] = -104.295
if 'live_wind_speed' not in st.session_state: st.session_state['live_wind_speed'] = 15.0
if 'live_wind_dir' not in st.session_state: st.session_state['live_wind_dir'] = 225.0

# --- FUNCTIONS ---
def get_risk_at_point(lat, lon):
    if not os.path.exists(RISK_MAP_PATH): return 0.0
    try:
        with rasterio.open(RISK_MAP_PATH) as src:
            row, col = src.index(lon, lat)
            if 0 <= row < src.height and 0 <= col < src.width:
                return float(src.read(1)[row, col])
            return 0.0
    except: return 0.0

@st.cache_data(ttl=600) 
def get_dynamic_satellite_view(lat, lon):
    try:
        delta = 0.008 
        bbox = f"{lon-delta},{lat-delta},{lon+delta},{lat+delta}"
        url = f"{ESRI_BASE_URL}?bbox={bbox}&bboxSR=4326&size=600,600&format=jpg&f=image"
        resp = requests.get(url, timeout=5)
        return Image.open(BytesIO(resp.content)) if resp.status_code == 200 else None
    except: return None

def img_to_base64(img):
    buf = BytesIO(); img.save(buf, format="PNG"); return base64.b64encode(buf.getvalue()).decode()

def create_hud_compass(deg):
    fig = plt.figure(figsize=(1.5, 1.5), dpi=100)
    ax = fig.add_subplot(111, projection='polar')
    ax.set_theta_zero_location('N'); ax.set_theta_direction(-1); ax.set_axis_off()
    ax.annotate("", xy=(0, 0), xytext=(np.radians(deg), 0.9), arrowprops=dict(arrowstyle="<-", color='#D32F2F', lw=4, mutation_scale=15))
    ax.text(0, 1.3, "N", ha='center', va='center', fontsize=12, fontweight='bold', color='#333')
    buf = BytesIO(); plt.savefig(buf, format='png', transparent=True, bbox_inches='tight'); buf.seek(0)
    return Image.open(buf)

def get_live_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=wind_speed_10m,wind_direction_10m&wind_speed_unit=kn"
        return requests.get(url, timeout=3).json().get('current', None)
    except: return None

# --- SIDEBAR (DYNAMIC KEYS = NO STICKY BUGS) ---
with st.sidebar:
    st.header("📍 Target Selector")
    
    # We use the VALUE as the KEY. This forces the widget to be destroyed and recreated
    # whenever the value changes (e.g., from a map click), preventing the "revert" bug.
    curr_lat = st.session_state['lat_input']
    curr_lon = st.session_state['lon_input']
    curr_wind = st.session_state['live_wind_speed']
    curr_dir = st.session_state['live_wind_dir']

    # Input Widgets
    new_lat = st.number_input("Latitude", value=curr_lat, key=f"lat_{curr_lat}", format="%.5f")
    new_lon = st.number_input("Longitude", value=curr_lon, key=f"lon_{curr_lon}", format="%.5f")
    
    st.divider()
    new_wind = st.slider("Wind (kn)", 0.0, 50.0, value=curr_wind, key=f"w_{curr_wind}")
    new_dir = st.slider("Direction (°)", 0, 360, value=int(curr_dir), key=f"d_{curr_dir}")

    # Manual Update Logic (If user types in sidebar)
    if new_lat != curr_lat: st.session_state['lat_input'] = new_lat; st.rerun()
    if new_lon != curr_lon: st.session_state['lon_input'] = new_lon; st.rerun()
    if new_wind != curr_wind: st.session_state['live_wind_speed'] = new_wind; st.rerun()
    if new_dir != curr_dir: st.session_state['live_wind_dir'] = new_dir; st.rerun()

# --- MAIN PAGE ---
st.title("📡 Manzanillo Digital Twin")
col_main, col_vis = st.columns([2, 1], gap="medium")

with col_main:
    # HUD
    risk_val = get_risk_at_point(st.session_state['lat_input'], st.session_state['lon_input'])
    risk_col = "#d9534f" if risk_val > 50 else "#f0ad4e" if risk_val > 20 else "#222"
    comp_b64 = img_to_base64(create_hud_compass(st.session_state['live_wind_dir']))
    
    st.markdown(f"""
    <div class="hud-box">
        <div class="hud-metric"><span class="hud-label">LATITUDE</span><span class="hud-value">{st.session_state['lat_input']:.4f}</span></div>
        <div class="hud-metric"><span class="hud-label">LONGITUDE</span><span class="hud-value">{st.session_state['lon_input']:.4f}</span></div>
        <div class="hud-metric"><span class="hud-label">RISK INDEX</span><span class="hud-value" style="color: {risk_col};">{risk_val:.0f}</span></div>
        <div class="hud-metric"><span class="hud-label">WIND</span><span class="hud-value">{st.session_state['live_wind_speed']:.1f} kn</span></div>
        <img src="data:image/png;base64,{comp_b64}" class="compass-img">
    </div>""", unsafe_allow_html=True)

    # MAP RENDER
    m = folium.Map(location=[st.session_state['lat_input'], st.session_state['lon_input']], zoom_start=13, tiles="CartoDB dark_matter")
    
    # 1. ADD MOUSE POSITION (COORDINATE NOTIFIER)
    # We add this BEFORE other layers to ensure it registers
    MousePosition(
        position='topright',
        separator=' | ',
        empty_string='NaN',
        lng_first=False,
        num_digits=5,
        prefix='Coordinates: ',
        lat_formatter="function(num) {return L.Util.formatNum(num, 5);};",
        lng_formatter="function(num) {return L.Util.formatNum(num, 5);};"
    ).add_to(m)

    m.get_root().html.add_child(folium.Element("<style>.leaflet-container { cursor: crosshair !important; }</style>"))
    
    folium.Marker([st.session_state['lat_input'], st.session_state['lon_input']], 
                  icon=folium.Icon(color='red', icon='crosshairs', prefix='fa')).add_to(m)
    
    if os.path.exists(RISK_MAP_PATH):
        try:
            with rasterio.open(RISK_MAP_PATH) as src:
                d = src.read(1); norm = np.clip(d, 0, 100)/100.0; c = plt.get_cmap('inferno')(norm)
                c[..., 3] = np.where(d<15, 0.0, 0.6)
                folium.raster_layers.ImageOverlay(c, [[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]], opacity=0.7).add_to(m)
        except: pass

    # STATIC KEY FOR MAP (Stops Flashing/Resetting)
    # We depend on st.rerun() to update the marker position naturally
    map_out = st_folium(m, height=500, width="100%", key="risk_dashboard_map", returned_objects=["last_clicked"])

    # CLICK LOGIC
    if map_out and map_out.get("last_clicked"):
        click = map_out["last_clicked"]
        
        # Check if this click is NEW (Different from current state)
        if (abs(click["lat"] - st.session_state['lat_input']) > 0.00001 or 
            abs(click["lng"] - st.session_state['lon_input']) > 0.00001):
            
            # Update State
            st.session_state['lat_input'] = click["lat"]
            st.session_state['lon_input'] = click["lng"]
            
            # Fetch Weather
            wx = get_live_weather(click["lat"], click["lng"])
            if wx:
                st.session_state['live_wind_speed'] = float(wx['wind_speed_10m'])
                st.session_state['live_wind_dir'] = float(wx['wind_direction_10m'])
            
            # Rerun: This triggers the Sidebar (above) to rebuild with NEW KEYS
            # because 'curr_lat' has changed. This is what fixes the Sticky/Revert bug.
            st.rerun()

with col_vis:
    st.markdown("<b>🛰️ Visual Recon</b>", unsafe_allow_html=True)
    sat = get_dynamic_satellite_view(st.session_state['lat_input'], st.session_state['lon_input'])
    if sat: st.image(sat, caption="Targeted Feed", use_container_width=True)