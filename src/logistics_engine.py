import osmnx as ox
import networkx as nx
import os
import math
from shapely.geometry import Point, Polygon

class LogisticsRouter:
    def __init__(self):
        """
        Manages real-world asset deployment with OPTIMIZED OBSTACLE AVOIDANCE.
        """
        self.graph = None
        self._load_network()
        
        self.BASES = {
            "TANKER": {"lat": 19.1438, "lon": -104.5596, "name": "Manzanillo Intl Airport (ZLO)"}, 
            "ENGINE-A": {"lat": 19.0520, "lon": -104.3140, "name": "Bomberos Manzanillo Central"}, 
            "ENGINE-B": {"lat": 19.1150, "lon": -104.3390, "name": "Station 2 - Santiago"},       
            "CREW-ZULU": {"lat": 19.0980, "lon": -104.2850, "name": "Foward Ops Base"},           
            "DRONE-X1": {"lat": 19.0600, "lon": -104.2950, "name": "Port Command"}                
        }
        
        self.SPEEDS = {"Air": 250.0, "Road": 50.0, "Offroad": 15.0}

    def _load_network(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            graph_path = os.path.join(base_dir, "data", "processed", "manzanillo_drive.graphml")
            if os.path.exists(graph_path):
                self.graph = ox.load_graphml(graph_path)
            else:
                self.graph = None
        except: self.graph = None

    def calculate_route(self, lat_target, lon_target, asset_id, avoid_polygon=None):
        base_key = "TANKER" if "TANKER" in asset_id else asset_id
        if base_key not in self.BASES:
            if "ENGINE" in asset_id: base_key = "ENGINE-A"
            elif "CREW" in asset_id: base_key = "CREW-ZULU"
            else: base_key = "ENGINE-A"
        start = self.BASES[base_key]
        
        # 1. AIR UNITS
        if "TANKER" in asset_id or "DRONE" in asset_id:
            return self._make_direct_route(start, lat_target, lon_target, self.SPEEDS["Air"], "Air Direct")

        # 2. GROUND UNITS (Smart Avoidance)
        if self.graph:
            try:
                routing_graph = self.graph
                
                # --- OPTIMIZATION: SMART BUFFER ---
                if avoid_polygon and len(avoid_polygon) > 3:
                    try:
                        poly = Polygon(avoid_polygon)
                        
                        # Shrink the "Kill Zone" slightly (buffer(-0.0001)) approx 10m
                        # This prevents blocking a road just because the fire perimeter "touches" it.
                        # Only blocks roads that go THROUGH the fire.
                        buffered_poly = poly.buffer(-0.0001) 
                        
                        if not buffered_poly.is_empty:
                            unsafe_nodes = [n for n, d in self.graph.nodes(data=True) if buffered_poly.contains(Point(d['y'], d['x']))]
                            if unsafe_nodes:
                                routing_graph = self.graph.subgraph([n for n in self.graph.nodes if n not in unsafe_nodes])
                    except: pass 

                # Find Nodes
                orig_node = ox.distance.nearest_nodes(routing_graph, start['lon'], start['lat'])
                dest_node = ox.distance.nearest_nodes(routing_graph, lon_target, lat_target)
                
                # Calculate Path
                node_path = nx.shortest_path(routing_graph, orig_node, dest_node, weight='length')
                road_dist_m = nx.path_weight(routing_graph, node_path, weight='length')
                
                # Build Geometry
                path_coords = [(start['lat'], start['lon'])]
                for n in node_path:
                    node = routing_graph.nodes[n]
                    path_coords.append((node['y'], node['x']))
                path_coords.append((lat_target, lon_target))
                
                # Metrics
                last_node = routing_graph.nodes[dest_node]
                hike_km = self._haversine(last_node['y'], last_node['x'], lat_target, lon_target)
                total_km = (road_dist_m / 1000.0) + hike_km
                
                duration = int(
                    ((road_dist_m/1000.0) / self.SPEEDS["Road"] * 60) + 
                    (hike_km / self.SPEEDS["Offroad"] * 60) + 2
                )
                
                return {
                    "origin": start['name'],
                    "distance_km": round(total_km, 2),
                    "duration_min": max(1, duration),
                    "path": path_coords,
                    "type": "Road (Smart)"
                }
            except Exception as e:
                pass 
        
        return self._make_direct_route(start, lat_target, lon_target, self.SPEEDS["Offroad"], "Direct (Nav Fail)")

    def _make_direct_route(self, start, lat_target, lon_target, speed_kmh, mode):
        dist_km = self._haversine(start['lat'], start['lon'], lat_target, lon_target)
        return {
            "origin": start['name'],
            "distance_km": round(dist_km, 2),
            "duration_min": max(1, int((dist_km / speed_kmh) * 60) + 2),
            "path": [(start['lat'], start['lon']), (lat_target, lon_target)],
            "type": mode
        }

    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c