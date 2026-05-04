import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from aws_discovery_worker import AWSDiscoveryWorker

def test_arcgis():
    worker = AWSDiscoveryWorker()
    # Test coordinates for Oklahoma City Capitol
    lat, lon = 35.4822, -97.5028
    target_id = "test_okc"
    
    print(f"Testing ArcGIS harvest for {lat}, {lon}...")
    path = worker.harvest_imagery(lat, lon, target_id)
    
    if path and os.path.exists(path):
        print(f"Success! Image saved to: {path}")
        print(f"File size: {os.path.getsize(path)} bytes")
    else:
        print("Failed to harvest imagery.")

if __name__ == "__main__":
    test_arcgis()
