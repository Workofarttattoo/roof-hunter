import sys

def apply_phases():
    path = 'roof_hunter/src/weather_twin/roof_hunter_digital_twin.py'
    lines = open(path).readlines()
    new_lines = []

    for line in lines:
        new_lines.append(line)

        # Phase 1
        if 'hail_score = (hail_score * 0.7) + (xg_boost * 0.3)' in line:
            new_lines.append('        from roof_hunter.ml.calibration import ProbabilityCalibrator\n')
            new_lines.append('\n')
            new_lines.append('        if hasattr(self, "calibrator") and self.calibrator:\n')
            new_lines.append('            hail_score = self.calibrator.transform([hail_score])[0]\n')

        # Phase 2 & 3
        if 'if best_cell:' in line:
            # We need to find the specific 'if best_cell:' in _apply_radar_localization
            # The one at line 400ish
            pass

    # Actually let's use a more robust way for Phase 2 & 3
    final_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        final_lines.append(line)

        if 'hail_score = (hail_score * 0.7) + (xg_boost * 0.3)' in line:
            final_lines.append('        from roof_hunter.ml.calibration import ProbabilityCalibrator\n')
            final_lines.append('\n')
            final_lines.append('        if hasattr(self, "calibrator") and self.calibrator:\n')
            final_lines.append('            hail_score = self.calibrator.transform([hail_score])[0]\n')

        if 'if best_cell:' in line and i > 350: # Ensure we are in _apply_radar_localization
            # Look ahead for the distance calculation to replace
            j = i + 1
            while j < len(lines) and 'dist = self._haversine_km' not in lines[j]:
                j += 1

            if j < len(lines) and 'dist = self._haversine_km' in lines[j]:
                # Insert Phase 2
                final_lines.append('            from roof_hunter.core.storm_motion import project_storm_cell\n')
                final_lines.append('\n')
                final_lines.append('            future_lat, future_lon = project_storm_cell(best_cell, minutes=30)\n')
                final_lines.append('\n')
                final_lines.append('            dist = self._haversine_km(\n')
                final_lines.append('                state.latitude,\n')
                final_lines.append('                state.longitude,\n')
                final_lines.append('                future_lat,\n')
                final_lines.append('                future_lon\n')
                final_lines.append('            )\n')

                # Insert Phase 3 growth detection
                final_lines.append('            growth = best_cell.get("dbz_current", 0) - best_cell.get("dbz_prev", 0)\n')
                final_lines.append('\n')
                final_lines.append('            if growth > 5:\n')
                final_lines.append('                current_score = min(1.0, current_score + 0.15)\n')

                # Skip the old dist line
                i = j

        # Enhanced lock condition (Phase 3)
        if 'if dist < 10:' in line and i > 350:
             # Find the block and replace or append
             pass

        i += 1

    with open(path, 'w') as f:
        f.writelines(final_lines)

apply_phases()
