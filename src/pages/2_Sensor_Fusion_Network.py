import streamlit as st
import folium
from folium.plugins import MousePosition
from streamlit_folium import st_folium
import streamlit.components.v1 as components
import rasterio
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.cm as cm
import os
from io import BytesIO
from PIL import Image

# 1. CONFIGURATION
st.set_page_config(
    layout="wide", 
    page_title="Manzanillo Sensor Command", 
    page_icon="📡",
    initial_sidebar_state="expanded"
)

# PATH SETUP
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))
RISK_MAP_PATH = os.path.join(PROJECT_ROOT, "data/processed/daily_fire_risk_map.tif")

# --- CUSTOM CSS (MATCHING PAGE 1 EXACTLY) ---
st.markdown("""
<style>
    /* 1. SIDEBAR: Shrink to 160px */
    [data-testid="stSidebar"] { min-width: 160px !important; max-width: 160px !important; }
    [data-testid="stSidebar"] * { font-size: 0.8rem !important; }
    
    /* 2. MAIN CONTAINER */
    .block-container { 
        padding-top: 1rem; 
        padding-bottom: 1rem; 
        padding-left: 1rem !important; 
        padding-right: 1rem !important;
    }
    
    /* 3. COMPACT HEADER */
    .compact-header {
        font-size: 1.4rem;
        font-weight: 700;
        margin-bottom: 5px;
        margin-top: -10px;
        border-bottom: 2px solid #f0f2f6;
    }
    
    /* 4. SENSOR HUD */
    .sensor-hud {
        display: flex;
        gap: 15px;
        background: #f8f9fa;
        padding: 8px 12px;
        border-radius: 6px;
        border: 1px solid #ddd;
        margin-bottom: 10px;
    }
    .hud-item { line-height: 1.1; }
    .hud-label { font-size: 0.65rem; color: #666; font-weight: 700; text-transform: uppercase; }
    .hud-value { font-size: 0.95rem; font-weight: 700; color: #222; font-family: monospace; }

    /* 5. CSS LEGEND (RED-ONLY / TRUNCATED) */
    .legend-container {
        font-family: sans-serif;
        margin-top: 8px;
        width: 100%;
    }
    .legend-title {
        font-size: 0.7rem;
        font-weight: 700;
        color: #444;
        margin-bottom: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .legend-bar {
        height: 12px;
        width: 100%;
        border-radius: 3px;
        /* TRUNCATED INFERNO GRADIENT (Black -> Purple -> Red) NO YELLOW */
        background: linear-gradient(90deg, 
            #000004 0%, 
            #420a68 33%, 
            #932667 66%, 
            #dd513a 100%);
        border: 1px solid #aaa;
    }
    .legend-labels {
        display: flex;
        justify-content: space-between;
        margin-top: 4px;
        font-size: 0.6rem;
        color: #555;
        font-weight: 600;
    }
    .legend-note {
        font-size: 0.7rem;
        color: #666;
        margin-top: 5px;
        font-style: italic;
        background-color: #fff3cd;
        padding: 4px 8px;
        border-radius: 4px;
        border: 1px solid #ffeeba;
    }
</style>
""", unsafe_allow_html=True)

# 2. SENSOR NETWORK DEFINITION
SENSORS = [
    {
        "id": "SAT-001",
        "name": "Strategic Satellite Recon",
        "lat": 19.0500, 
        "lon": -104.3000,
        "type": "satellite_static",
        "icon": "globe",
        "color": "blue",
        "url": "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export?bbox=-104.38,19.03,-104.25,19.12&bboxSR=4326&size=800,500&format=jpg&f=image"
    },
    {
        "id": "MET-004",
        "name": "Live Wind Vector Model",
        "lat": 19.1015, 
        "lon": -104.3550,
        "type": "windy_map",
        "icon": "flag",
        "color": "green",
        "url": "https://embed.windy.com/embed2.html?lat=19.050&lon=-104.316&detailLat=19.050&detailLon=-104.316&width=650&height=450&zoom=11&level=surface&overlay=wind&product=ecmwf&menu=&message=&marker=&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=kt&metricTemp=%C2%B0C&radarRange=-1"
    },
    {
        "id": "CAM-009",
        "name": "Port North Gate (Drone Patrol)",
        "lat": 19.0850,
        "lon": -104.2850,
        "type": "youtube",
        "icon": "camera",
        "color": "red",
        "url": "https://www.youtube.com/embed/w2JVJvTRLL0?autoplay=1&mute=1&controls=0&loop=1&playlist=w2JVJvTRLL0" 
    },
    {
        "id": "CAM-012",
        "name": "Laguna Expansion (Vaso II)",
        "lat": 19.0300, 
        "lon": -104.2600,
        "type": "youtube",
        "icon": "camera",
        "color": "red",
        "url": "https://www.youtube.com/embed/Os26_zm65-c?autoplay=1&mute=1&controls=0&loop=1&playlist=Os26_zm65-c"
    }
]

# --- SIDEBAR (CONTROLS) ---
st.sidebar.markdown("### Network Controls")
st.sidebar.info("Click markers on the map to switch live feeds.")
st.sidebar.markdown("---")
show_inactive = st.sidebar.checkbox("Show Inactive Nodes", value=False)
show_heatmap = st.sidebar.checkbox("Overlay Heatmap", value=True)

# --- LAYOUT ---
st.markdown('<div class="compact-header">📡 Sensor Fusion Network</div>', unsafe_allow_html=True)

# 2-COLUMN LAYOUT
col_map, col_feed = st.columns([1.5, 2], gap="medium")

# --- 1. SENSOR MAP (LEFT) ---
with col_map:
    # Header & Legend (Dynamic)
    if not show_heatmap:
        st.markdown("**Network Topology**")
    
    # Initialize Map
    m = folium.Map(location=[19.0600, -104.2800], zoom_start=11, tiles="CartoDB dark_matter")
    
    # ADD GPS COORDINATES ON HOVER
    formatter = "function(num) {return L.Util.formatNum(num, 4) + ' º ';};"
    MousePosition(
        position='topright',
        separator=' | ',
        empty_string='NaN',
        lng_first=False,
        num_digits=20,
        prefix='GPS: ',
        lat_formatter=formatter,
        lng_formatter=formatter,
    ).add_to(m)
    
    # HEATMAP OVERLAY
    if show_heatmap and os.path.exists(RISK_MAP_PATH):
        try:
            with rasterio.open(RISK_MAP_PATH) as src:
                data = src.read(1)
                data = np.nan_to_num(data, nan=0.0)
                data = np.maximum(data, 0)
                
                # Normalize & Truncate (Red-Line Mode)
                min_val, max_val = np.min(data), np.max(data)
                if max_val > min_val:
                    norm_data = (data - min_val) / (max_val - min_val)
                    
                    # 1. Physics: Wind Multiplier (Get from State or Default)
                    wind_speed = st.session_state.get('live_wind_speed', 5.0)
                    wind_factor = 1.0 + (wind_speed / 30.0)
                    norm_data = norm_data * wind_factor
                    
                    # 2. Clip top end at 0.8 (Removes Yellow/White)
                    norm_data = np.clip(norm_data * 0.8, 0, 0.8) 
                else:
                    norm_data = np.zeros_like(data)
                
                # Apply Inferno
                cmap = cm.get_cmap('inferno')
                colored_data = cmap(norm_data)
                
                bounds = [[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]]
                
                folium.raster_layers.ImageOverlay(
                    image=colored_data,
                    bounds=bounds,
                    opacity=0.6,
                    name="AI Risk Heatmap"
                ).add_to(m)
                
            # --- VECTOR LEGEND (MATCHING PAGE 1) ---
            st.markdown("""
            <div class="legend-container">
                <div class="legend-title">OPERATIONAL THREAT INDEX (OTI)</div>
                <div class="legend-bar"></div>
                <div class="legend-labels">
                    <span>WATER</span>
                    <span>LOW</span>
                    <span>MODERATE</span>
                    <span>HIGH</span>
                    <span>CRITICAL</span>
                </div>
                <div class="legend-note">
                    ⚠️ <b>ANALYST NOTE:</b> High-intensity zones in lagoons/wetlands indicate <b>Dense Biomass (Mangroves)</b>.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error loading Heatmap: {e}")

    # PLOT SENSORS
    for s in SENSORS:
        folium.Marker(
            [s['lat'], s['lon']], 
            tooltip=f"{s['id']}: {s['name']}", 
            icon=folium.Icon(color=s['color'], icon=s['icon'], prefix='fa')
        ).add_to(m)

    # RENDER MAP
    map_output = st_folium(m, height=400, width="100%", returned_objects=["last_object_clicked_tooltip"])

# --- 2. FEED VIEWER (RIGHT) ---
with col_feed:
    selected_sensor = SENSORS[0]
    
    if map_output and map_output.get("last_object_clicked_tooltip"):
        clicked_id = map_output["last_object_clicked_tooltip"].split(":")[0]
        found = next((s for s in SENSORS if s["id"] == clicked_id), None)
        if found:
            selected_sensor = found

    st.markdown(f"**Target Feed: {selected_sensor['name']}**")
    
    st.markdown(f"""
    <div class="sensor-hud">
        <div class="hud-item">
            <div class="hud-label">NODE ID</div>
            <div class="hud-value">{selected_sensor['id']}</div>
        </div>
        <div class="hud-item">
            <div class="hud-label">TYPE</div>
            <div class="hud-value">{selected_sensor['type'].split('_')[0].upper()}</div>
        </div>
        <div class="hud-item">
            <div class="hud-label">SIGNAL</div>
            <div class="hud-value" style="color:green;">● ONLINE</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if selected_sensor['type'] == 'satellite_static':
        st.image(selected_sensor['url'], caption="Strategic Optical Recon (Esri)", use_container_width=True)

    elif selected_sensor['type'] == 'windy_map':
        components.iframe(selected_sensor['url'], height=400)
        st.caption("ℹ️ Live Particle Simulation")

    elif selected_sensor['type'] == 'youtube':
        components.iframe(selected_sensor['url'], height=400)
        st.caption("🔴 Live RTSP Stream")