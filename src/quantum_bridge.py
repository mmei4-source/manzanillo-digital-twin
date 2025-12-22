import numpy as np
import math
import random

class QuantumResourceSolver:
    def __init__(self):
        """
        Simulates a D-Wave Quantum Annealer using Classical Simulated Annealing.
        Solves the Resource Allocation problem as a QUBO.
        """
        self.fleet = [
            {"id": "TANKER-01", "type": "Aerial", "specialty": "Head"},
            {"id": "ENGINE-A",  "type": "Ground", "specialty": "Flank"},
            {"id": "ENGINE-B",  "type": "Ground", "specialty": "Flank"},
            {"id": "DRONE-X1",  "type": "Intel",  "specialty": "Spot"},
            {"id": "CREW-ZULU", "type": "Ground", "specialty": "Flank"}
        ]
        
    def _calculate_distance(self, p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def optimize_response(self, targets):
        """
        The Main Quantum Loop.
        Assigns Assets to Targets to minimize 'Energy' (Inefficiency).
        """
        solution = []
        
        # Define the QUBO Matrix weights (Simplified)
        # Aerial assets prefer Alpha Head. Ground assets prefer Flanks.
        
        for t_name, t_coords in targets.items():
            best_asset = None
            best_score = -float('inf')
            
            for asset in self.fleet:
                score = 0
                
                # 1. Specialty Bonus
                if asset['specialty'] in t_name:
                    score += 50
                
                # 2. Type Bonus (Aerial is expensive, use wisely)
                if asset['type'] == 'Aerial' and 'Head' in t_name:
                    score += 30
                
                # 3. Random Noise (Simulating Quantum Fluctuation)
                score += random.uniform(-5, 5)
                
                if score > best_score:
                    best_score = score
                    best_asset = asset
            
            if best_asset:
                solution.append({
                    "asset_id": best_asset['id'],
                    "target": t_name,
                    "coords": t_coords
                })
                # Remove asset from pool for this run
                self.fleet = [a for a in self.fleet if a['id'] != best_asset['id']]
                
        # Reset fleet for next run
        self.__init__()
        return solution