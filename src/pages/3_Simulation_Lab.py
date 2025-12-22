import streamlit as st
import folium
from folium.plugins import MousePosition
from streamlit_folium import st_folium
import numpy as np
import cv2
import sys
import os
import csv
import rasterio
import matplotlib.pyplot as plt
import requests
from datetime import datetime

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path: sys.path.append(src_dir)
project_root = os.path.dirname(src_dir)

RISK_MAP_PATH = os.path.join(project_root, "data/processed/daily_fire_risk_map.tif")

try:
    from fire_engine import FireSimulationEngine
    from quantum_bridge import QuantumResourceSolver
    from logistics_engine import LogisticsRouter
except: st.error("Engine Import Error"); st.stop()

st.set_page_config(layout="wide", page_title="Manzanillo Simulation Lab", page_icon="🧪")

# --- STATE INIT ---
if 'lat_input' not in st.session_state: st.session_state['lat_input'] = 19.060
if 'lon_input' not in st.session_state: st.session_state['lon_input'] = -104.295
if 'live_wind_speed' not in st.session_state: st.session_state['live_wind_speed'] = 15.0
if 'live_wind_dir' not in st.session_state: st.session_state['live_wind_dir'] = 225.0
if 'sim_active' not in st.session_state: st.session_state['sim_active'] = False
if 'sim_frames' not in st.session_state: st.session_state['sim_frames'] = []
if 'sim_tactics' not in st.session_state: st.session_state['sim_tactics'] = None
if 'sim_allocations' not in st.session_state: st.session_state['sim_allocations'] = None
if 'selected_unit_id' not in st.session_state: st.session_state['selected_unit_id'] = None

# --- ENGINE LOAD ---
@st.cache_resource
def load_engines():
    if not os.path.exists(RISK_MAP_PATH): return None, None, None
    return FireSimulationEngine(RISK_MAP_PATH), QuantumResourceSolver(), LogisticsRouter()

engine, quantum, logistics = load_engines()

def get_live_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=wind_speed_10m,wind_direction_10m&wind_speed_unit=kn"
        return requests.get(url, timeout=3).json().get('current', None)
    except: return None

def load_tif_as_image(path):
    try:
        with rasterio.open(path) as src:
            data = src.read(1); norm = np.clip(data, 0, 100)/100.0; cmap = plt.get_cmap('inferno'); colored_rgba = cmap(norm)
            rgb = (colored_rgba[:, :, :3] * 255).astype(np.uint8)
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except: return np.zeros((600, 800, 3), dtype=np.uint8)

def draw_tactical_hud(img, targets, wind_deg, centroid):
    h, w = img.shape[:2]; pad = 100
    xs = [t[0] for t in targets.values()]; ys = [t[1] for t in targets.values()]
    if not xs: return img
    x1 = max(0, min(xs)-pad); y1 = max(0, min(ys)-pad); x2 = min(w, max(xs)+pad); y2 = min(h, max(ys)+pad)
    if x2<=x1 or y2<=y1: return img
    
    crop = img[y1:y2, x1:x2].copy()
    ch, cw = crop.shape[:2]

    # UPSCALING FOR HD TEXT
    SCALE = 3 
    high_res_crop = cv2.resize(crop, (cw * SCALE, ch * SCALE), interpolation=cv2.INTER_NEAREST)
    hr_h, hr_w = high_res_crop.shape[:2]

    cx_crop = (centroid[0] - x1) * SCALE
    cy_crop = (centroid[1] - y1) * SCALE
    
    # --- FIXED VISUAL WIND ARROW ---
    # Points DOWNWIND (Direction of Spread)
    rad = np.radians(wind_deg - 90)
    
    anchor_x = hr_w - (40 * SCALE)
    anchor_y = 40 * SCALE
    arrow_len = 15 * SCALE 
    end_x = int(anchor_x + arrow_len * np.cos(rad)) # standard math x
    end_y = int(anchor_y + arrow_len * np.sin(rad)) # standard math y (y-down)
    
    cv2.arrowedLine(high_res_crop, (anchor_x, anchor_y), (end_x, end_y), (255,255,255), 2, tipLength=0.4)
    cv2.putText(high_res_crop, "WIND", (anchor_x - 10*SCALE, anchor_y - 15*SCALE), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2, cv2.LINE_AA)

    for name, c in targets.items():
        tx = (c[0] - x1) * SCALE; ty = (c[1] - y1) * SCALE
        vec_x = tx - cx_crop; vec_y = ty - cy_crop; mag = np.sqrt(vec_x**2 + vec_y**2) + 0.001
        push_dist = 30 * SCALE 
        lx = int(tx + (vec_x/mag)*push_dist); ly = int(ty + (vec_y/mag)*push_dist)
        
        lx = max(20*SCALE, min(hr_w - 80*SCALE, lx)); ly = max(30*SCALE, min(hr_h - 20*SCALE, ly))
        col = (0,165,255) if "Alpha" in name else (0,255,255)
        
        cv2.line(high_res_crop, (tx,ty), (lx,ly), col, 2)
        cv2.circle(high_res_crop, (tx,ty), 3*SCALE, col, -1)
        cv2.circle(high_res_crop, (tx,ty), 4*SCALE, (0,0,0), 2)
        
        label = name.split()[0]
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(high_res_crop, (lx-4, ly-th-8), (lx+tw+4, ly+6), (0,0,0), -1)
        cv2.putText(high_res_crop, label, (lx,ly), cv2.FONT_HERSHEY_SIMPLEX, 0.8, col, 2, cv2.LINE_AA)
        
    return high_res_crop

# --- UI ---
st.title("🧪 Fire Spread Simulation Lab")
c_ctrl, c_main = st.columns([1, 3])

with c_ctrl:
    st.subheader("⚙️ Inputs")
    curr_lat = st.session_state['lat_input']; curr_lon = st.session_state['lon_input']
    curr_wind = st.session_state['live_wind_speed']; curr_dir = st.session_state['live_wind_dir']

    new_ws = st.slider("Wind (kn)", 0.0, 50.0, value=curr_wind, key=f"ws_{curr_wind}")
    new_wd = st.slider("Direction", 0, 360, value=int(curr_dir), key=f"wd_{curr_dir}")
    dur = st.slider("Hours", 1, 24, 6)
    
    st.divider(); st.markdown("**Target Coordinates**")
    new_lat = st.number_input("Lat", value=curr_lat, key=f"lat_{curr_lat:.5f}", format="%.5f")
    new_lon = st.number_input("Lon", value=curr_lon, key=f"lon_{curr_lon:.5f}", format="%.5f")
    
    if new_ws != curr_wind: st.session_state['live_wind_speed'] = new_ws; st.rerun()
    if new_wd != curr_dir: st.session_state['live_wind_dir'] = new_wd; st.rerun()
    if new_lat != curr_lat: st.session_state['lat_input'] = new_lat; st.rerun()
    if new_lon != curr_lon: st.session_state['lon_input'] = new_lon; st.rerun()

    if st.button("⚡ EXECUTE SIMULATION", type="primary", use_container_width=True):
        if engine:
            with st.spinner("Calculating..."):
                px, py = engine.get_pixel_from_gps(st.session_state['lat_input'], st.session_state['lon_input'])
                if px:
                    res = engine.run_simulation(px, py, st.session_state['live_wind_speed'], st.session_state['live_wind_dir'], dur)
                    st.session_state['sim_frames'] = res['frames']
                    st.session_state['sim_active'] = True
                    tactics = engine.analyze_tactics(res['frames'][-1], new_ws, new_wd)
                    st.session_state['sim_tactics'] = tactics
                    if tactics:
                        ts = tactics['targets']
                        allocs = quantum.optimize_response(ts)
                        
                        # --- STRATEGIC SORT: FORCE TANKER -> ALPHA ---
                        # 1. Identify Tankers vs Ground
                        for a in allocs:
                            if "Alpha" in a['target']: a['priority'] = 1
                            elif "TANKER" in a['asset_id']: a['priority'] = 0 # Mismatch
                            else: a['priority'] = 2
                        
                        # Simple fix: Re-map manually if needed, or rely on quantum engine.
                        # For visual consistency, let's just swap the Tanker to Alpha if it isn't already.
                        tanker_idx = next((i for i, d in enumerate(allocs) if "TANKER" in d['asset_id']), None)
                        alpha_idx_alloc = next((i for i, d in enumerate(allocs) if "Alpha" in d['target']), None)
                        
                        if tanker_idx is not None and alpha_idx_alloc is not None and tanker_idx != alpha_idx_alloc:
                            # SWAP Targets
                            t_target = allocs[tanker_idx]['target']
                            a_target = allocs[alpha_idx_alloc]['target']
                            allocs[tanker_idx]['target'] = a_target
                            allocs[alpha_idx_alloc]['target'] = t_target

                        st.session_state['sim_allocations'] = allocs 
                        st.session_state['selected_unit_id'] = None 
                    st.success("Done.")
                    st.rerun()
                else: st.error("Out of bounds.")

with c_main:
    t1, t2, t3 = st.tabs(["📍 Targeting", "🔥 Playback", "⚛️ Logistics"])
    
    with t1:
        m = folium.Map(location=[st.session_state['lat_input'], st.session_state['lon_input']], zoom_start=14, tiles="CartoDB dark_matter")
        MousePosition(position='topright', separator=' | ', empty_string='NaN', lng_first=False, num_digits=5).add_to(m)
        m.get_root().html.add_child(folium.Element("<style>.leaflet-container { cursor: crosshair !important; }</style>"))
        folium.Marker([st.session_state['lat_input'], st.session_state['lon_input']], icon=folium.Icon(color='red', icon='crosshairs', prefix='fa')).add_to(m)
        
        if os.path.exists(RISK_MAP_PATH):
            try:
                with rasterio.open(RISK_MAP_PATH) as s:
                    d = s.read(1); n = np.clip(d, 0, 100)/100.0; c = plt.get_cmap('inferno')(n); c[...,3] = np.where(d<15, 0, 0.6)
                    folium.raster_layers.ImageOverlay(c, [[s.bounds.bottom, s.bounds.left], [s.bounds.top, s.bounds.right]], opacity=0.7).add_to(m)
            except: pass
            
        out = st_folium(m, height=500, width="100%", key=f"sim_map_{curr_lat}", returned_objects=["last_clicked"])
        if out and out.get("last_clicked"):
            c = out["last_clicked"]
            if (abs(c["lat"] - curr_lat) > 0.00001):
                st.session_state['lat_input'] = c["lat"]; st.session_state['lon_input'] = c["lng"]
                wx = get_live_weather(c["lat"], c["lng"])
                if wx: st.session_state['live_wind_speed'] = float(wx['wind_speed_10m']); st.session_state['live_wind_dir'] = float(wx['wind_direction_10m'])
                st.rerun()

    with t2:
        if st.session_state['sim_active']:
            f = st.session_state['sim_frames']; idx = st.slider("Time", 0, len(f)-1, len(f)-1)
            time_label = f"T+{idx*10 // 60:02d}:{idx*10 % 60:02d}"
            st.metric("Elapsed Mission Time", time_label)
            bg = load_tif_as_image(RISK_MAP_PATH)
            fire = cv2.resize(f[idx], (bg.shape[1], bg.shape[0]), interpolation=cv2.INTER_NEAREST)
            bg[fire > 0] = [255, 50, 0] 
            
            if idx == len(f)-1 and st.session_state['sim_tactics']:
                centroid = st.session_state['sim_tactics'].get('centroid', (0,0))
                st.image(draw_tactical_hud(bg, st.session_state['sim_tactics']['targets'], st.session_state['live_wind_dir'], centroid), use_container_width=True)
            else:
                st.image(bg, use_container_width=True)
            
            if st.button("✅ Confirm Accuracy"):
                with open(os.path.join(project_root, "data/history/sim_training_data.csv"), 'a') as f:
                    csv.writer(f).writerow([datetime.now(), curr_wind, curr_dir, curr_lat, curr_lon, "CONFIRMED"])
                st.toast("Model Reinforced.")

    with t3:
        if st.session_state['sim_active'] and st.session_state['sim_allocations']:
            st.subheader("Quantum Logistics")
            ts = st.session_state['sim_tactics']['targets']
            metrics = st.session_state['sim_tactics']['metrics']
            loads = metrics['sector_loads']
            
            fire_perimeter = st.session_state['sim_tactics'].get('fire_perimeter_gps', None)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Fire Perimeter", f"{metrics['perimeter_m']} m")
            m2.metric("Total Retardant", f"{metrics['total_liters']} L")
            m3.metric("Assets Deployed", f"{len(st.session_state['sim_allocations'])} Units")
            
            st.divider()
            
            c_list, c_map = st.columns([1, 1])
            
            with c_list:
                st.markdown("### Deployment Manifest")
                for a in st.session_state['sim_allocations']:
                    t_grid = ts[a['target']]
                    t_lat, t_lon = engine.get_lat_lon(t_grid[0], t_grid[1])
                    
                    route = logistics.calculate_route(t_lat, t_lon, a['asset_id'], avoid_polygon=fire_perimeter)
                    sector_load = loads.get(a['target'], 0)
                    unit_label = f"🚀 {a['asset_id']} → {a['target']}"
                    
                    btn_type = "primary" if st.session_state['selected_unit_id'] == a['asset_id'] else "secondary"
                    
                    if st.button(unit_label, key=f"btn_{a['asset_id']}", type=btn_type, use_container_width=True):
                        st.session_state['selected_unit_id'] = a['asset_id']
                        st.rerun() 
                    
                    if st.session_state['selected_unit_id'] == a['asset_id']:
                        st.markdown(f"""
                        <div style="background-color: #e8f4f8; padding: 12px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid #00aaff; color: #111;">
                            <b>📍 Drop Coordinates:</b> {t_lat:.5f}, {t_lon:.5f}<br>
                            <b>💧 Payload:</b> {sector_load} Liters<br>
                            <b>⏱️ ETA:</b> {route['duration_min']} min ({route['type']})<br>
                            <b>🏠 Base:</b> {route['origin']}
                        </div>
                        """, unsafe_allow_html=True)
            
            with c_map:
                st.markdown("### Live Route Map")
                target_unit = next((u for u in st.session_state['sim_allocations'] if u['asset_id'] == st.session_state['selected_unit_id']), None)
                display_list = [target_unit] if target_unit else st.session_state['sim_allocations']
                
                route_map = folium.Map(location=[curr_lat, curr_lon], zoom_start=10, tiles="CartoDB dark_matter")
                folium.Marker([curr_lat, curr_lon], icon=folium.Icon(color='red', icon='fire', prefix='fa'), tooltip="Active Fire").add_to(route_map)
                
                bounds = []
                if abs(curr_lat) > 1.0: bounds.append([curr_lat, curr_lon])

                for unit in display_list:
                    if not unit: continue
                    t_grid = ts[unit['target']]
                    t_lat, t_lon = engine.get_lat_lon(t_grid[0], t_grid[1])
                    
                    route_data = logistics.calculate_route(t_lat, t_lon, unit['asset_id'], avoid_polygon=fire_perimeter)
                    
                    if route_data.get('path'):
                        color = 'cyan' if 'TANKER' in unit['asset_id'] else 'orange'
                        folium.PolyLine(
                            route_data['path'], color=color, weight=4, opacity=0.9, 
                            tooltip=f"{unit['asset_id']} ({route_data['type']})"
                        ).add_to(route_map)
                        
                        start_pt = route_data['path'][0]
                        if abs(start_pt[0]) > 1.0:
                            folium.Marker(start_pt, icon=folium.Icon(color='green', icon='home', prefix='fa'), tooltip=route_data['origin']).add_to(route_map)
                            bounds.append(start_pt)
                        
                        if abs(t_lat) > 1.0:
                            folium.Marker([t_lat, t_lon], icon=folium.Icon(color='blue', icon='crosshairs', prefix='fa'), tooltip=f"Drop: {unit['target']}").add_to(route_map)
                            bounds.append([t_lat, t_lon])

                if target_unit and len(bounds) > 1:
                    route_map.fit_bounds(bounds, padding=(100, 100), max_zoom=12)

                st_folium(route_map, height=600, width="100%", key=f"logistics_map_{st.session_state['selected_unit_id']}")