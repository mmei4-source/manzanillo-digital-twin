import numpy as np
import rasterio
import scipy.ndimage
import cv2
import os
import math

class FireSimulationEngine:
    def __init__(self, risk_map_path):
        self.risk_map_path = risk_map_path
        self.transform = None
        self.crs = None
        self.risk_grid = self._load_geospatial_data()
        self.base_spread_prob = 0.15
        self.wind_factor = 0.08
        
    def _load_geospatial_data(self):
        if not os.path.exists(self.risk_map_path): return np.zeros((600, 800))
        try:
            with rasterio.open(self.risk_map_path) as src:
                self.transform = src.transform
                self.crs = src.crs
                data = src.read(1)
                return data / 255.0 if data.max() > 1 else data
        except: return np.zeros((600, 800))

    def get_pixel_from_gps(self, lat, lon):
        if self.transform is None: return None, None
        try:
            row, col = rasterio.transform.rowcol(self.transform, lon, lat)
            if 0 <= row < self.risk_grid.shape[0] and 0 <= col < self.risk_grid.shape[1]:
                return col, row
            return None, None
        except: return None, None

    def get_lat_lon(self, x, y):
        if self.transform is None: return 0, 0
        lon, lat = rasterio.transform.xy(self.transform, y, x, offset='center')
        return lat, lon

    def _generate_wind_kernel(self, speed, direction):
        # Convert Met Wind (FROM) to Spread Vector (TO)
        # Met: 0=N, 90=E. Image: 0=E, 90=S (Y-down).
        # We need to carefully align this.
        # Wind From North (0) -> Spreads South (Down, +Y)
        # rad 0 -> cos(0)=1 (X?), sin(0)=0. 
        # Let's use standard polar: angle from X-axis (Right).
        # Met 0 (North) is 270 deg polar.
        # Met 90 (East) is 360/0 deg polar.
        # Spread is opposite: North Wind spreads South (90 deg polar).
        
        # simplified alignment for simulation visuals:
        # Assuming wind_dir is standard 0-360 input.
        rad = math.radians(direction - 90) 
        
        u = speed * math.cos(rad) * self.wind_factor 
        v = speed * math.sin(rad) * self.wind_factor 
        
        k = np.array([[0.1, 0.1, 0.1], [0.1, 0.0, 0.1], [0.1, 0.1, 0.1]])
        
        # Apply wind bias
        if v > 0: k[2, :] += v      # South bias
        if v < 0: k[0, :] += abs(v) # North bias
        if u > 0: k[:, 2] += u      # East bias
        if u < 0: k[:, 0] += abs(u) # West bias
        return k

    def run_simulation(self, start_x, start_y, wind_speed, wind_dir, duration_hours):
        fire_grid = np.zeros_like(self.risk_grid)
        if 0 <= start_y < fire_grid.shape[0] and 0 <= start_x < fire_grid.shape[1]:
            fire_grid[start_y, start_x] = 1.0 
        
        kernel = self._generate_wind_kernel(wind_speed, wind_dir)
        steps = int(duration_hours * 6) 
        frames = []
        current_state = fire_grid.copy()
        frames.append((current_state * 255).astype(np.uint8))
        
        for _ in range(steps):
            neighbor_influence = scipy.ndimage.convolve(current_state, kernel, mode='constant')
            prob_map = neighbor_influence * (self.risk_grid + 0.1) 
            random_roll = np.random.rand(*prob_map.shape)
            new_ignitions = (prob_map > random_roll) & (self.risk_grid > 0.1)
            current_state = np.maximum(current_state, new_ignitions.astype(float))
            frames.append((current_state * 255).astype(np.uint8))
            
        return {'frames': frames}

    def analyze_tactics(self, fire_mask, wind_speed, wind_dir):
        contours, _ = cv2.findContours(fire_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return None
            
        largest = max(contours, key=cv2.contourArea)
        M = cv2.moments(largest)
        if M["m00"] == 0: return None
        cx = int(M["m10"] / M["m00"]); cy = int(M["m01"] / M["m00"])
        
        gps_polygon = []
        for pt in largest[::5, 0, :]:
            lat, lon = self.get_lat_lon(pt[0], pt[1])
            gps_polygon.append((lat, lon))
            
        perimeter_pixels = cv2.arcLength(largest, True)
        perimeter_meters = perimeter_pixels * 20.0 
        total_retardant = perimeter_meters * 5.0 
        
        loads = {
            'Alpha Head': int(total_retardant * 0.50),
            'Bravo Flank': int(total_retardant * 0.25),
            'Charlie Flank': int(total_retardant * 0.25)
        }
        
        pts = largest[:, 0, :]
        
        # --- FIXED VECTOR MATH ---
        # We need the vector pointing DOWNWIND (Direction OF Spread)
        # If Wind Dir = 225 (SW), Spread is towards 45 (NE).
        # Cos/Sin needs to align with Image X/Y (Y is down).
        
        rad = math.radians(wind_dir - 90)
        vx = math.cos(rad)
        vy = math.sin(rad) # Positive Y is DOWN in images
        
        # Project all contour points onto the spread vector
        # The point with the MAX projection is furthest DOWNWIND -> ALPHA
        projections = np.dot(pts - [cx, cy], [vx, vy])
        alpha_idx = np.argmax(projections)
        
        # Perpendicular vector for flanks
        px, py = -vy, vx
        cross_prods = np.dot(pts - [cx, cy], [px, py])
        bravo_idx = np.argmin(cross_prods)
        charlie_idx = np.argmax(cross_prods)
        
        return {
            'targets': {
                'Alpha Head': tuple(pts[alpha_idx]),
                'Bravo Flank': tuple(pts[bravo_idx]),
                'Charlie Flank': tuple(pts[charlie_idx])
            },
            'centroid': (cx, cy),
            'fire_perimeter_gps': gps_polygon,
            'metrics': {
                'perimeter_m': int(perimeter_meters),
                'total_liters': int(total_retardant),
                'sector_loads': loads
            }
        }