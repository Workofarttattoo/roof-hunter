"""3-Day Forward Outlook: Oklahoma and Texas High-Risk Sweep."""

import sys
import json
from pathlib import Path
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor

# Syncing paths
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.weather_twin.s2s_pattern_matcher import calculate_s2s_outlook

# Regional Hubs for Public Safety Sweep
REGIONAL_HUBS = [
    {"city": "Oklahoma City", "lat": 35.4676, "lon": -97.5164, "state": "OK"},
    {"city": "Tulsa", "lat": 36.1540, "lon": -95.9928, "state": "OK"},
    {"city": "Moore", "lat": 35.3394, "lon": -97.4867, "state": "OK"},
    {"city": "Edmond", "lat": 35.6528, "lon": -97.4781, "state": "OK"},
    {"city": "Dallas", "lat": 32.7767, "lon": -96.7970, "state": "TX"},
    {"city": "Fort Worth", "lat": 32.7555, "lon": -97.3308, "state": "TX"},
    {"city": "Austin", "lat": 30.2672, "lon": -97.7431, "state": "TX"},
    {"city": "San Antonio", "lat": 29.4241, "lon": -98.4936, "state": "TX"},
    {"city": "Waco", "lat": 31.5493, "lon": -97.1467, "state": "TX"}
]

def predict_hub_risk(hub):
    city = hub['city']
    state = hub['state']
    lat, lon = hub['lat'], hub['lon']
    
    today = date.today()
    
    # We simulate for each of the next 3 days
    daily_risks = []
    for i in range(1, 4):
        target_date = today + timedelta(days=i)
        try:
            outlook = calculate_s2s_outlook(target_date, lat, lon)
            daily_risks.append({
                "date": str(target_date),
                "score": outlook['s2s_risk_score'],
                "intensity": outlook.get('intensity_cat', 'Low')
            })
        except:
            daily_risks.append({"date": str(target_date), "score": 0.0, "intensity": "Low"})
            
    # Max risk over 3 days
    peak = max(daily_risks, key=lambda x: x['score'])
    
    return {
        "city": city,
        "state": state,
        "peak_risk_date": peak['date'],
        "peak_score": peak['score'],
        "peak_intensity": peak['intensity'],
        "daily_breakdown": daily_risks
    }

def run_forward_outlook():
    print("\nINITIATING 3-DAY SEVERE WEATHER SWEEP (OK + TX)...")
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(predict_hub_risk, hub) for hub in REGIONAL_HUBS]
        for f in futures:
            res = f.result()
            results.append(res)
            print(f"ANALYSED: {res['city']}, {res['state']} | Peak: {res['peak_score']:.1f} ({res['peak_intensity']}) on {res['peak_risk_date']}")
            
    # Sort by risk
    results.sort(key=lambda x: x['peak_score'], reverse=True)
    
    print("\n" + "="*50)
    print("3-DAY SEVERE RISK LEADERBOARD")
    for r in results[:5]: # Top 5 High-Risk Hubs
        print(f"{r['city']}, {r['state']} -> RISK: {r['peak_score']:.1f} | DATE: {r['peak_risk_date']} | IMPACT: {r['peak_intensity']}")
    print("="*50)
    
    with open("three_day_outlook.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_forward_outlook()
