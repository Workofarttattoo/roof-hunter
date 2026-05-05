import sys

path = 'roof_hunter/src/weather_twin/roof_hunter_digital_twin.py'
content = open(path).read()

# Phase 1
old1 = '        hail_score = (hail_score * 0.7) + (xg_boost * 0.3)'
new1 = """        hail_score = (hail_score * 0.7) + (xg_boost * 0.3)
        from roof_hunter.ml.calibration import ProbabilityCalibrator

        if hasattr(self, "calibrator") and self.calibrator:
            hail_score = self.calibrator.transform([hail_score])[0]"""

if old1 in content:
    content = content.replace(old1, new1, 1)

# Find the index of "if best_cell:" in _apply_radar_localization
lines = content.splitlines()
target_idx = -1
for idx, line in enumerate(lines):
    if idx > 400 and 'if best_cell:' in line:
        # Check ahead for the specific distance call
        if idx + 1 < len(lines) and 'dist = self._haversine_km(state.latitude, state.longitude, best_cell' in lines[idx+1]:
             target_idx = idx
             break

if target_idx != -1:
    content = '\n'.join(lines[:target_idx+1]) + '\n'

    # Append Phase 2 & 3 + rest of class
    rest = """            from roof_hunter.core.storm_motion import project_storm_cell

            future_lat, future_lon = project_storm_cell(best_cell, minutes=30)

            dist = self._haversine_km(
                state.latitude,
                state.longitude,
                future_lat,
                future_lon
            )
            growth = best_cell.get("dbz_current", 0) - best_cell.get("dbz_prev", 0)

            if growth > 5:
                current_score = min(1.0, current_score + 0.15)

            if dist < 15 and best_cell.get("max_reflectivity_dbz", 0) > 55 and growth > 3:
                current_score = max(current_score, 0.85)
                return current_score, f"RADAR_LOCKED: {best_cell['storm_cell_id']} at {dist:.1f}km. dBZ={best_cell.get('max_reflectivity_dbz')}"

            elif dist < 30: # Within 30km (The "Proximity Zone")
                return min(1.0, current_score + 0.1), f"RADAR_PROXIMITY: Cell {best_cell['storm_cell_id']} at {dist:.1f}km"

        return current_score, ""

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

    def _estimate_hail_core(self,
                            state: ForecastState,
                            analysis: Dict[str, Any],
                            hail_score: float,
                            pressure_trend: Optional[float],
                            moisture_factor: float) -> Dict[str, Any]:
        base_radius_m = 150.0
        if hail_score > 0.7:
            radius_m = 25.0 + (1.0 - hail_score) * 200.0
        elif hail_score > 0.4:
            radius_m = 100.0 + (0.7 - hail_score) * 200.0
        else:
            radius_m = 250.0 + (0.4 - hail_score) * 300.0

        if pressure_trend is not None and pressure_trend < -1.0:
            radius_m = max(20.0, radius_m - 50.0)

        if moisture_factor > 0.75:
            radius_m = max(20.0, radius_m - 25.0)

        confidence = min(1.0, hail_score * 0.75 + moisture_factor * 0.15 + 0.1)
        distance_ft = round(radius_m * 3.28084, 1)

        core_note = 'Localized hail core proxy. Not radar-resolved to 10 ft, but useful for short-range lead scoring.'
        if confidence > 0.7:
            core_note = 'Strong localized hail core signature. Use this for high-priority lead targeting.'
        elif confidence > 0.4:
            core_note = 'Moderate hail core likelihood. Validate with radar or observations.'

        return {
            'hail_core_confidence': round(confidence, 3),
            'hail_core_radius_ft': distance_ft,
            'hail_core_note': core_note,
            'note': core_note,
        }

    @classmethod
    def load_forecast_from_payload(cls, payload: Dict[str, Any]) -> 'RoofHunterWeatherTwin':
        states = [ForecastState.from_dict(item) for item in payload['forecast']]
        return cls(states)

    @classmethod
    def load_forecast(cls, path: Path) -> 'RoofHunterWeatherTwin':
        with path.open('r', encoding='utf-8') as f:
            payload = json.load(f)
        return cls.load_forecast_from_payload(payload)

    def export_results(self, path: Path) -> None:
        with path.open('w', encoding='utf-8') as f:
            json.dump({'history': self.history}, f, indent=2)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description='Run Roof Hunter weather twin simulation.')
    parser.add_argument('--forecast', type=Path, default=Path('roof_hunter_forecast.json'))
    parser.add_argument('--output', type=Path, default=Path('roof_hunter_results.json'))
    args = parser.parse_args()

    twin = RoofHunterWeatherTwin.load_forecast(args.forecast)
    history = twin.simulate()
    twin.export_results(args.output)
    print(f'Roof Hunter simulated {len(history)} forecast steps and saved results to {args.output}')


if __name__ == '__main__':
    main()"""
    content += rest

with open(path, 'w') as f:
    f.write(content)
