import sys

path = 'roof_hunter/src/weather_twin/roof_hunter_digital_twin.py'
lines = open(path).readlines()
new_lines = []

i = 0
while i < len(lines):
    line = lines[i]
    new_lines.append(line)

    # Phase 1: Calibration
    if 'hail_score = (hail_score * 0.7) + (xg_boost * 0.3)' in line:
        new_lines.append('        from roof_hunter.ml.calibration import ProbabilityCalibrator\n\n')
        new_lines.append('        if hasattr(self, "calibrator") and self.calibrator:\n')
        new_lines.append('            hail_score = self.calibrator.transform([hail_score])[0]\n')

    # Phase 2 & 3: Storm Motion & Growth
    if 'if best_cell:' in line and i > 350:
        # Move forward to find the distance calculation
        j = i + 1
        found_dist = False
        while j < len(lines) and 'if best_cell:' not in lines[j] and 'def ' not in lines[j]:
            if 'dist = self._haversine_km(state.latitude, state.longitude, best_cell[' in lines[j]:
                found_dist = True
                break
            j += 1

        if found_dist:
            # Add everything from i+1 to j-1
            for k in range(i+1, j):
                new_lines.append(lines[k])

            # Replace j with Phase 2 & 3
            new_lines.append('            from roof_hunter.core.storm_motion import project_storm_cell\n\n')
            new_lines.append('            future_lat, future_lon = project_storm_cell(best_cell, minutes=30)\n\n')
            new_lines.append('            dist = self._haversine_km(\n')
            new_lines.append('                state.latitude,\n')
            new_lines.append('                state.longitude,\n')
            new_lines.append('                future_lat,\n')
            new_lines.append('                future_lon\n')
            new_lines.append('            )\n')
            new_lines.append('            growth = best_cell.get("dbz_current", 0) - best_cell.get("dbz_prev", 0)\n\n')
            new_lines.append('            if growth > 5:\n')
            new_lines.append('                current_score = min(1.0, current_score + 0.15)\n')

            i = j # Move pointer to the line we just replaced (conceptually)

    # Enhanced lock condition
    if 'if dist < 10:' in line and i > 350:
        # Replace the condition and possibly the body
        new_lines[-1] = '            if dist < 15 and best_cell.get("max_reflectivity_dbz", 0) > 55 and growth > 3:\n'
        new_lines.append('                current_score = max(current_score, 0.85)\n')
        # Skip the original body of if dist < 10:
        # It was:
        #   boost = 0.25 * (1.0 - dist / 10.0)
        #   new_score = min(1.0, current_score + boost)
        #   if best_cell.get('max_reflectivity_dbz', 0) > 60:
        #       new_score = max(new_score, 0.85)
        #   return new_score, ...

        # We need to find where that block ends.
        # Let's find 'return'
        k = i + 1
        while k < len(lines) and 'return ' not in lines[k]:
            k += 1
        if k < len(lines):
             new_lines.append('                ' + lines[k].strip() + '\n')
             i = k

    i += 1

with open(path, 'w') as f:
    f.writelines(new_lines)
