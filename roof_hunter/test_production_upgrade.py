import sys
import os
import math

# Add the current directory to sys.path so we can import roof_hunter
sys.path.append(os.getcwd())

def test_calibration():
    print("Testing Calibration...")
    from roof_hunter.ml.calibration import ProbabilityCalibrator
    calib = ProbabilityCalibrator()
    preds = [0.1, 0.4, 0.35, 0.8]
    actuals = [0, 0, 1, 1]
    calib.fit(preds, actuals)
    transformed = calib.transform([0.5])
    print(f"Transformed 0.5: {transformed}")

def test_storm_motion():
    print("Testing Storm Motion...")
    from roof_hunter.core.storm_motion import project_storm_cell
    cell = {
        "center_lat": 35.0,
        "center_lon": -97.0,
        "speed_kmh": 60,
        "direction_deg": 0 # East
    }
    new_lat, new_lon = project_storm_cell(cell, minutes=60)
    print(f"New position: {new_lat}, {new_lon}")

def test_targeting():
    print("Testing Targeting...")
    from roof_hunter.core.targeting import generate_targets, classify_target
    properties = [
        {"lat": 35.1, "lon": -97.0, "vulnerability": 0.8},
        {"lat": 35.5, "lon": -97.0, "vulnerability": 0.2}
    ]
    targets = generate_targets(properties, 35.0, -97.0, 0.8)
    print(f"Targets: {targets}")
    print(f"Classify 0.85: {classify_target(0.85)}")

def test_feedback():
    print("Testing Feedback...")
    from roof_hunter.core.feedback import log_outcome
    outcome = log_outcome(0.8, 1, 5000)
    print(f"Outcome: {outcome}")

if __name__ == "__main__":
    try:
        import sklearn
        import numpy
        import fastapi

        test_calibration()
        test_storm_motion()
        test_targeting()
        test_feedback()
        print("Production upgrade modules smoke test passed!")
    except ImportError as e:
        print(f"Skipping some tests due to missing dependency: {e}")
        # Still test the ones that don't need heavy deps if possible
        test_storm_motion()
        test_targeting()
        test_feedback()
