# 🔥 Manzanillo Digital Twin: Wildfire & Logistics Command

**Version:** 1.2 (Cloud-Ready)
**Status:** Operational

## 1. System Overview
This platform acts as a central nervous system for port resilience. It combines three advanced technologies into a single dashboard:
1.  **AI Risk Modeling:** Uses Sentinel-2 satellite imagery to detect biomass and wildfire potential.
2.  **Physics Simulation:** Predicts fire spread in real-time based on live wind and terrain data.
3.  **Quantum Logistics:** Optimizes the deployment of emergency assets (Tankers, Engines, Drones) using QUBO algorithms.

---

## 2. Quick Start (Cloud Deployment)
This app is deployed to Streamlit Cloud, simply visit https://manzanillo-digital-twin.streamlit.app/Simulation_Lab. No installation is required.

**For Local Development:**
1.  **Clone the Repo:**
    ```bash
    git clone [https://github.com/YOUR_ORG/manzanillo-digital-twin.git](https://github.com/YOUR_ORG/manzanillo-digital-twin.git)
    cd manzanillo-digital-twin
    ```
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Launch the App:**
    ```bash
    streamlit run src/Home.py
    ```

---

## 3. Data Maintenance (CRITICAL)
**⚠️ IMPORTANT:** The satellite data processing pipeline runs **locally**. It does not run on the cloud server due to the size of raw satellite files (>1GB).

### How to Update the Risk Map (Monthly/Weekly)
To refresh the `daily_fire_risk_map.tif` with new vegetation data, the maintainer must:

1.  **Download New Data:**
    * Go to [Copernicus Open Access Hub](https://scihub.copernicus.eu/).
    * Download the latest **Sentinel-2 L2A** product for Manzanillo (Tile: `13QEB`).
    * You will get a large `.zip` file (approx 1.1 GB).

2.  **Place Data:**
    * Move the `.zip` file into: `data/raw/sentinel/`
    * *Note: Delete old zip files to save space.*

3.  **Run the Processor:**
    ```bash
    python src/update_risk_map.py
    ```
    *This script unzips the data, calculates NDVI, runs the Random Forest model, and generates a new TIF.*

4.  **Push to Cloud:**
    * The script overwrites `data/processed/daily_fire_risk_map.tif`.
    * Commit and push this single file to GitHub to update the live app.

---

## 4. Operational Modules

### 🧪 Simulation Lab (`src/pages/3_Simulation_Lab.py`)
The core predictive engine.
* **Physics:** Cellular Automata model based on Rothermel equations.
* **Inputs:** Live wind speed/direction (Open-Meteo API) + Terrain Slope (SRTM).
* **Output:** 6-hour spread prediction + "Alpha/Bravo/Charlie" tactical targets.

### ⚛️ Quantum Logistics (`src/logistics_engine.py`)
Optimizes asset routing.
* **Graph Network:** Uses `manzanillo_drive.graphml` (OpenStreetMap data) for routing.
* **Logic:**
    * **Air Units:** Take direct paths.
    * **Ground Units:** Use A* pathfinding on the road network.
    * **Avoidance:** Ground units automatically reroute *around* the predicted fire perimeter.

---

## 5. Directory Structure
```text
/
├── src/
│   ├── Home.py                 # Main Entry Point
│   ├── fire_engine.py          # Physics Simulation Logic
│   ├── logistics_engine.py     # Routing & Graph Logic
│   ├── quantum_bridge.py       # Resource Allocation Solver
│   └── pages/                  # Streamlit Dashboard Pages
├── data/
│   ├── processed/
│   │   ├── daily_fire_risk_map.tif  # The "Brain" (8MB) - MUST EXIST
│   │   └── manzanillo_drive.graphml # Road Network (10MB) - MUST EXIST
│   └── raw/                    # (Ignored by Git) Place 1GB Zips here
└── requirements.txt            # Dependency List
