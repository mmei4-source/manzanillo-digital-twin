import sys
print("-> Script initialized. Importing libraries... (This may take a moment)")

try:
    import osmnx as ox
    import os
    import time
    print("-> Libraries imported successfully.")
except ImportError as e:
    print(f"❌ CRITICAL ERROR: Missing libraries. {e}")
    print("Run: pip install osmnx networkx")
    sys.exit(1)

def rebuild_manzanillo_graph():
    print("\n" + "="*40)
    print("🗺️  MANZANILLO MAP REPAIR TOOL")
    print("="*40)
    
    # 1. Setup Paths
    output_dir = os.path.join("data", "processed")
    if not os.path.exists(output_dir):
        print(f"-> Creating directory: {output_dir}")
        os.makedirs(output_dir)
    else:
        print(f"-> Directory exists: {output_dir}")

    # 2. Download
    place_name = "Manzanillo, Colima, Mexico"
    print(f"\n📡 CONNECTING TO OPENSTREETMAP...")
    print(f"   Target: {place_name}")
    print(f"   Type:   Drive (Roads only)")
    print("   ...Downloading data (Please wait, do not close)...")
    
    start_time = time.time()
    try:
        # Requesting the graph
        G = ox.graph_from_place(place_name, network_type='drive')
        elapsed = time.time() - start_time
        print(f"✅ DOWNLOAD COMPLETE in {elapsed:.1f} seconds.")
    except Exception as e:
        print(f"\n❌ DOWNLOAD FAILED: {e}")
        print("Check your internet connection or try a VPN if blocked.")
        return

    # 3. Save
    output_path = os.path.join(output_dir, "manzanillo_drive.graphml")
    print(f"\n💾 SAVING FILE...")
    print(f"   Path: {output_path}")
    
    try:
        ox.save_graphml(G, output_path)
        file_size = os.path.getsize(output_path) / 1024  # KB
        print(f"✅ SAVE SUCCESSFUL!")
        print(f"   File Size: {file_size:.0f} KB")
        print(f"   Nodes: {len(G.nodes)}")
        print(f"   Edges: {len(G.edges)}")
    except Exception as e:
        print(f"❌ SAVE FAILED: {e}")

if __name__ == "__main__":
    rebuild_manzanillo_graph()
    print("\n-> Script finished. You may close this window.")