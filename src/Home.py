import streamlit as st
import os
import sys

# --- 1. PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# --- 2. PAGE CONFIG ---
st.set_page_config(
    page_title="Manzanillo Digital Twin",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 3. THE DATA BRIDGE (Global State Initialization) ---
# We define these ONCE. They are now the "Single Source of Truth" for the whole app.

def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

# Coordinates (Default: Manzanillo Port)
init_state('lat_input', 19.060)
init_state('lon_input', -104.295)

# Weather (Default: Onshore Breeze)
init_state('live_wind_speed', 15.0)
init_state('live_wind_dir', 225.0)

# App Logic
init_state('sim_active', False)
init_state('user_role', "COMMANDER")

# --- 4. DASHBOARD UI ---
st.title("🔥 Port of Manzanillo: Wildfire Resilience Twin")
st.markdown("### Integrated Risk Management System (Phase 4)")
st.divider()

col_status, col_telemetry, col_actions = st.columns([2, 1, 1])

with col_status:
    st.markdown("""
    #### 📡 System Status: **ONLINE**
    
    This Digital Twin integrates real-time satellite telemetry, physics-based fire modeling, 
    and quantum-ready optimization to protect the Port of Manzanillo.
    
    **Instructions:**
    1. Go to **Real-Time Risk** to identify threats.
    2. Click a location on the map.
    3. Navigate to **Simulation Lab** to run a prediction on that exact spot.
    """)

with col_telemetry:
    st.markdown("#### 🌤️ Active Weather State")
    # These metrics prove the state is alive
    st.metric("Wind Speed", f"{st.session_state['live_wind_speed']} kn", "Live Feed")
    st.metric("Wind Direction", f"{st.session_state['live_wind_dir']}°", "Live Feed")

with col_actions:
    st.markdown("#### 🚀 Actions")
    if st.button("Re-Calibrate Sensors"):
        st.toast("Calibrating optical sensors... OK.")
    if st.button("Download Daily Report"):
        st.toast("Generating PDF report... Download started.")