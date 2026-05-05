import sys

path = 'roof_hunter/src/weather_twin/roof_hunter_digital_twin.py'
lines = open(path).readlines()
new_lines = []

i = 0
while i < len(lines):
    line = lines[i]

    # Phase 1: Calibration
    if 'hail_score = (hail_score * 0.7) + (xg_boost * 0.3)' in line:
        new_lines.append(line)
        new_lines.append('        from roof_hunter.ml.calibration import ProbabilityCalibrator\n\n')
        new_lines.append('        if hasattr(self, "calibrator") and self.calibrator:\n')
        new_lines.append('            hail_score = self.calibrator.transform([hail_score])[0]\n')
        i += 1
        continue

    # Phase 2 & 3: Storm Motion & Growth
    if 'if best_cell:' in line and i > 350:
        # Check if it's the right if best_cell: (the one that has haversine after it)
        j = i + 1
        is_target = False
        while j < len(lines) and 'if best_cell:' not in lines[j] and 'def ' not in lines[j]:
             if 'dist = self._haversine_km(state.latitude, state.longitude, best_cell[' in lines[j]:
                 is_target = True
                 break
             j += 1

        if is_target:
            new_lines.append(line)
            # Find the dist calculation line
            while 'dist = self._haversine_km' not in lines[i]:
                i += 1
                new_lines.append(lines[i])

            # Now lines[i] is the dist line. Replace it.
            new_lines[-1] = '            from roof_hunter.core.storm_motion import project_storm_cell\n\n'
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

            # Now continue to find 'if dist < 10:'
            while 'if dist < 10:' not in lines[i]:
                i += 1
                new_lines.append(lines[i])

            # Replace 'if dist < 10:'
            new_lines[-1] = '            if dist < 15 and best_cell.get("max_reflectivity_dbz", 0) > 55 and growth > 3:\n'
            new_lines.append('                current_score = max(current_score, 0.85)\n')

            # Find the return line
            while 'return ' not in lines[i]:
                i += 1

            new_lines.append('                ' + lines[i].strip() + '\n')
            i += 1
            continue

    new_lines.append(line)
    i += 1

with open(path, 'w') as f:
    f.writelines(new_lines)
