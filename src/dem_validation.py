import rasterio
import numpy as np
from rasterio.warp import calculate_default_transform, reproject, Resampling
import matplotlib.pyplot as plt
import os

# --- Configuration ---
# UPDATED PATHS: These are now relative to your root folder
INEGI_PATH = 'data/raw/inegi_cem/Colima_r15m.tif'
SRTM_PATH = 'data/raw/srtm/N19W105.hgt' 
OUTPUT_DIR = 'data/processed/'
DELTA_OUTPUT = os.path.join(OUTPUT_DIR, 'dem_delta_analysis.tif')
PLOT_OUTPUT = os.path.join(OUTPUT_DIR, 'dem_validation_plot.png')

def validate_dem():
    print("--- Starting DEM Validation (INEGI vs SRTM) ---")
    
    # Check if files exist before trying to open
    if not os.path.exists(INEGI_PATH):
        raise FileNotFoundError(f"Could not find INEGI file at: {INEGI_PATH}")
    if not os.path.exists(SRTM_PATH):
        raise FileNotFoundError(f"Could not find SRTM file at: {SRTM_PATH}")

    # 1. Open the High-Res Reference (INEGI)
    with rasterio.open(INEGI_PATH) as dst:
        inegi_data = dst.read(1)
        inegi_meta = dst.meta.copy()
        print(f"Loaded INEGI CEM: {dst.width}x{dst.height} px | CRS: {dst.crs}")

        # 2. Open the Low-Res Benchmark (SRTM) and Reproject to match INEGI
        with rasterio.open(SRTM_PATH) as src:
            print(f"Loaded NASA SRTM: {src.width}x{src.height} px | CRS: {src.crs}")
            
            # Create an empty array to hold the reprojected SRTM data
            # This aligns the SRTM grid to match the INEGI grid exactly
            srtm_reprojected = np.zeros((dst.height, dst.width), dtype=np.float32)

            reproject(
                source=rasterio.band(src, 1),
                destination=srtm_reprojected,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst.transform,
                dst_crs=dst.crs,
                resampling=Resampling.bilinear
            )
            print("Reprojection complete. Grids aligned.")

    # 3. Calculate the Delta (Difference)
    # Mask out 'no data' values (usually very low negative numbers)
    # We filter out anything below -100m to avoid void data affecting stats
    valid_mask = (inegi_data > -100) & (srtm_reprojected > -100)
    
    if not np.any(valid_mask):
        print("Error: No valid overlapping data found between the two DEMs.")
        return

    # Calculate Delta: INEGI - SRTM
    delta = np.zeros_like(inegi_data, dtype=np.float32)
    delta[valid_mask] = inegi_data[valid_mask] - srtm_reprojected[valid_mask]

    # 4. Statistical Analysis for the Tech Note
    mean_error = np.mean(delta[valid_mask])
    mae = np.mean(np.abs(delta[valid_mask])) # Mean Absolute Error
    rmse = np.sqrt(np.mean(delta[valid_mask]**2))
    max_pos_diff = np.max(delta[valid_mask])
    max_neg_diff = np.min(delta[valid_mask])

    print("\n" + "="*40)
    print("VALIDATION RESULTS (Copy to Tech Note)")
    print("="*40)
    print(f"Mean Bias Error (MBE): {mean_error:.4f} meters")
    print(f"Mean Absolute Error (MAE): {mae:.4f} meters")
    print(f"Root Mean Sq Error (RMSE): {rmse:.4f} meters")
    print(f"Max Positive Delta (INEGI higher): {max_pos_diff:.2f} m")
    print(f"Max Negative Delta (SRTM higher): {max_neg_diff:.2f} m")
    print("="*40)

    # 5. Save the Delta Map (Evidence)
    inegi_meta.update({
        "driver": "GTiff",
        "height": dst.height,
        "width": dst.width,
        "transform": dst.transform,
        "dtype": "float32",
        "count": 1
    })

    with rasterio.open(DELTA_OUTPUT, "w", **inegi_meta) as dest:
        dest.write(delta, 1)
    
    print(f"\nDelta Map saved to: {DELTA_OUTPUT}")
    
    # 6. Quick Visualization
    plt.figure(figsize=(10, 6))
    plt.imshow(delta, cmap='RdBu', vmin=-20, vmax=20)
    plt.colorbar(label='Elevation Delta (m)')
    plt.title('DEM Validation: INEGI CEM - NASA SRTM')
    plt.xlabel('Longitude (px)')
    plt.ylabel('Latitude (px)')
    plt.tight_layout()
    plt.savefig(PLOT_OUTPUT)
    print(f"Validation plot saved to: {PLOT_OUTPUT}")
    print("Check the plot for 'stair-step' patterns in flat areas.")

if __name__ == "__main__":
    validate_dem()