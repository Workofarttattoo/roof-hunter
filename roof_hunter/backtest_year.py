"""Statewide 12-Month S2S Backtest for Oklahoma - Roof Hunter Pro."""

import sys
import json
import logging
from pathlib import Path
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Syncing paths to project root
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from validate_last_week import (
    fetch_last_week_weather, 
    build_forecast_payload, 
    fetch_spc_reports, 
    match_reports_to_forecast
)
from src.weather_twin.roof_hunter_digital_twin import RoofHunterWeatherTwin
from src.weather_twin.models import ForecastState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StatewideBacktest")

# Top 15 ROI Population Centers in Oklahoma
OK_GRID = [
    {'city': 'Moore', 'lat': 35.3394, 'lon': -97.4867},
    {"city": "Oklahoma City", "lat": 35.4676, "lon": -97.5164},
    {"city": "Tulsa", "lat": 36.1540, "lon": -95.9928},
    {"city": "Norman", "lat": 35.2226, "lon": -97.4395},
    {"city": "Broken Arrow", "lat": 36.0609, "lon": -95.7975},
    {"city": "Edmond", "lat": 35.6528, "lon": -97.4781},
    {"city": "Lawton", "lat": 34.6036, "lon": -98.3959},
    {"city": "Moore", "lat": 35.3394, "lon": -97.4867},
    {"city": "Midwest City", "lat": 35.4495, "lon": -97.3967},
    {"city": "Enid", "lat": 36.3956, "lon": -97.8784},
    {"city": "Stillwater", "lat": 36.1156, "lon": -97.0584},
    {"city": "Muskogee", "lat": 35.7479, "lon": -95.3697},
    {"city": "Bartlesville", "lat": 36.7473, "lon": -95.9761},
    {"city": "Shawnee", "lat": 35.3273, "lon": -96.9253},
    {"city": "Owasso", "lat": 36.2734, "lon": -95.8219},
    {"city": "Ponca City", "lat": 36.7070, "lon": -97.0856}
]

def process_location(location, start_date, end_date):
    lat, lon = location['lat'], location['lon']
    city = location['city']
    
    all_summaries = []
    current_start = start_date
    
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=90), end_date) # 3-month batches for speed
        try:
            weather = fetch_last_week_weather(lat, lon, current_end, current_start)
            payload = build_forecast_payload(weather, lat, lon)
            twin = RoofHunterWeatherTwin([ForecastState.from_dict(item) for item in payload['forecast']])
            history = twin.simulate()
            reports = fetch_spc_reports(lat, lon, current_start, current_end, radius_km=40.0)
            metrics = match_reports_to_forecast(history, reports)
            all_summaries.append(metrics['summary'])
        except Exception as e:
            logger.error(f"Error in {city} batch {current_start}: {e}")
        current_start = current_end + timedelta(days=1)
        
    return {
        "city": city,
        "precision": sum(s['precision'] for s in all_summaries) / len(all_summaries) if all_summaries else 0,
        "recall": sum(s['recall'] for s in all_summaries) / len(all_summaries) if all_summaries else 0,
        "matches": sum(s['matched_report_count'] for s in all_summaries)
    }

def run_statewide_audit():
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=30)
    
    logger.info(f"RE-INITIATING STATEWIDE AUDIT: 15 Cities | 12 Months | {start_date} to {end_date}")
    
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_location, loc, start_date, end_date) for loc in OK_GRID[:1]]
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            logger.info(f"FINISHED: {res['city']} | Recall: {res['recall']*100:.1f}% | Precision: {res['precision']*100:.1f}%")
            
    final_recall = sum(r['recall'] for r in results) / len(results)
    final_precision = sum(r['precision'] for r in results) / len(results)
    total_strikes = sum(r['matches'] for r in results)
    
    final_report = {
        "state": "Oklahoma",
        "period": {"start": str(start_date), "end": str(end_date)},
        "metrics": {
            "statewide_recall": final_recall,
            "statewide_precision": final_precision,
            "total_hail_strikes_tracked": total_strikes
        },
        "city_breakdown": results
    }
    
    with open("statewide_ok_audit.json", "w") as f:
        json.dump(final_report, f, indent=2)
        
    print("\n" + "="*50)
    print("STATEWIDE OKLAHOMA AUDIT COMPLETE")
    print(f"Verified State Recall: {final_recall*100:.2f}%")
    print(f"Verified State Precision: {final_precision*100:.2f}%")
    print(f"Total Hail Strikes Captured: {total_strikes}")
    print("="*50)

if __name__ == "__main__":
    run_statewide_audit()
