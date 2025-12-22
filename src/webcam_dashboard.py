import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components

# 1. CONFIGURATION
st.set_page_config(layout="wide", page_title="Manzanillo Sensor Command")

# 2. SENSOR DATA (The "Best of Both Worlds" Configuration)
data = [
    {
        "id": "sat1",
        "name": "Strategic Satellite View (Esri World Imagery)",
        "lat": 19.0500, 
        "lon": -104.3000,
        "type": "satellite_static",
        # Guaranteed Cloud-Free High-Res Map of Port Infrastructure
        "url": "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export?bbox=-104.38,19.03,-104.25,19.12&bboxSR=4326&size=800,500&format=jpg&f=image"
    },
    {
        "id": "windy1",
        "name": "Live Wind Vector (Windy.com)",
        "lat": 19.1015, 
        "lon": -104.3550,
        "type": "windy_map",
        # The "Particle Animation" Map - Always works, looks very high-tech
        "url": "https://embed.windy.com/embed2.html?lat=19.050&lon=-104.316&detailLat=19.050&detailLon=-104.316&width=650&height=450&zoom=11&level=surface&overlay=wind&product=ecmwf&menu=&message=&marker=&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=kt&metricTemp=%C2%B0C&radarRange=-1"
    },
    {
        "id": "cam_sim",
        "name": "Port Perimeter (Simulated Feed)",
        "lat": 19.0520, 
        "lon": -104.3150,
        "type": "youtube",
        # Reliable live ocean cam acting as a placeholder for future CCTV integration
        "url": "https://www.youtube.com/watch?v=F8mnWzR4fYo" 
    }
]

df = pd.DataFrame(data)

# 3. LAYOUT
st.title("🚢 Manzanillo Port Resilience: Integrated Sensor Grid")
st.markdown("**Status:** 🟢 Online | **Mode:** Strategic Command (Hybrid)")

col1, col2 = st.columns([2, 1]) 

# 4. MAP SECTION
with col1:
    st.subheader("Geospatial Network")
    # Center carefully to show all markers
    m = folium.Map(location=[19.08, -104.32], zoom_start=12)

    for index, row in df.iterrows():
        # Icon Logic to distinguish sensor types
        if row['type'] == 'satellite_static':
            color, icon = "blue", "globe"
        elif row['type'] == 'windy_map':
            color, icon = "green", "flag"  # Green flag for weather station
        else:
            color, icon = "orange", "video-camera" # Orange for video feed
            
        folium.Marker(
            [row['lat'], row['lon']],
            tooltip=f"{row['name']}",
            popup=row['name'], 
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(m)

    # Render map and listen for clicks
    map_output = st_folium(m, height=600, width="100%", returned_objects=["last_object_clicked_tooltip"])

# 5. FEED VIEWER
with col2:
    st.subheader("Optical Feed")
    
    # Logic: Default to Satellite (Row 0) unless clicked
    selected_node = df.iloc[0]
    
    if map_output and map_output.get("last_object_clicked_tooltip"):
        clicked_name = map_output["last_object_clicked_tooltip"]
        found = df[df['name'] == clicked_name]
        if not found.empty:
            selected_node = found.iloc[0]

    # Display Info
    st.info(f"📡 Signal: **{selected_node['name']}**")
    
    # --- DISPLAY LOGIC BASED ON TYPE ---
    if selected_node['type'] == 'satellite_static':
        # Display High-Res Static Map
        st.image(selected_node['url'], caption="High-Resolution Infrastructure View", use_container_width=True)
        st.caption("ℹ️ Source: Esri World Imagery (Calibrated for Port Infrastructure)")

    elif selected_node['type'] == 'windy_map':
        # Display Interactive Weather Map
        components.iframe(selected_node['url'], height=450)
        st.caption("✅ Live Wind Particle Simulation (Real-Time Model)")

    elif selected_node['type'] == 'youtube':
        # Display Live Video Simulation
        st.video(selected_node['url'], autoplay=True)
        st.caption("⚠️ SIMULATION: Placeholder for secure Port CCTV feed.")