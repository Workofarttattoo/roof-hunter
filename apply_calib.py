lines = open('roof_hunter/src/weather_twin/roof_hunter_digital_twin.py').readlines()
with open('roof_hunter/src/weather_twin/roof_hunter_digital_twin.py', 'w') as f:
    for line in lines:
        f.write(line)
        if 'hail_score = (hail_score * 0.7) + (xg_boost * 0.3)' in line:
            f.write('        from roof_hunter.ml.calibration import ProbabilityCalibrator\n\n')
            f.write('        if hasattr(self, "calibrator") and self.calibrator:\n')
            f.write('            hail_score = self.calibrator.transform([hail_score])[0]\n')
