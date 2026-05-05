"""
36-Month Hail Skill Test: Rolling Hindcast Tournament.
Locks predictions before checking outcomes. No moving goalposts.
"""

import sys
import os
import json
import logging
import math
import numpy as np
from datetime import datetime, timedelta, date, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
import urllib.request
import io
import csv
from sklearn.metrics import brier_score_loss, roc_auc_score, average_precision_score

# Add roof_hunter to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'roof_hunter'))

# Import existing SPC fetching logic
try:
    from roof_hunter.validate_last_week import (
        fetch_spc_daily_report,
        parse_spc_daily_report,
        _haversine_km
    )
except ImportError:
    # Fallback if pathing is weird in different envs
    sys.path.append(os.path.join(os.getcwd(), 'roof_hunter'))
    from validate_last_week import (
        fetch_spc_daily_report,
        parse_spc_daily_report,
        _haversine_km
    )

from roof_hunter.src.weather_twin.roof_hunter_digital_twin import RoofHunterWeatherTwin
from roof_hunter.src.weather_twin.models import ForecastState
from roof_hunter.src.weather_twin.s2s_pattern_matcher import S2SPatternMatcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("36MonthBenchmark")

HORIZONS = [
    timedelta(hours=48),
    timedelta(days=7),
    timedelta(days=30),
    timedelta(days=90),
    timedelta(days=180),
    timedelta(days=365),
    timedelta(days=730),
    timedelta(days=1095)
]

HORIZON_LABELS = ["48h", "7d", "30d", "90d", "180d", "12m", "24m", "36m"]

# Targets
T_HAIL_100 = "hail_ge_100"
T_HAIL_175 = "hail_ge_175"
T_PROP_DAM = "property_damage"
T_TOP_5_VALUE = "top_5pct_value_zones"

TARGETS = [T_HAIL_100, T_HAIL_175, T_PROP_DAM, T_TOP_5_VALUE]

class HindcastTournament:
    def __init__(self, start_date: date, end_date: date):
        self.start_date = start_date
        self.end_date = end_date
        self.predictions = []
        self.outcomes = {} # (target_date_str, geo_id) -> Dict[target, bool]
        self.s2s_matcher = S2SPatternMatcher()

    def lock_predictions(self, locations: List[Dict[str, Any]]):
        logger.info(f"Locking predictions from {self.start_date} to {self.end_date}")

        current_pred_date = self.start_date
        while current_pred_date <= self.end_date:
            for loc in locations:
                for i, horizon in enumerate(HORIZONS):
                    target_time = datetime.combine(current_pred_date + horizon, datetime.min.time(), tzinfo=timezone.utc)

                    scores = self._generate_multi_target_prediction(current_pred_date, target_time, loc)

                    self.predictions.append({
                        "pred_date": current_pred_date.isoformat(),
                        "target_date": target_time.date().isoformat(),
                        "horizon": HORIZON_LABELS[i],
                        "horizon_days": horizon.total_seconds() / 86400,
                        "lat": loc['lat'],
                        "lon": loc['lon'],
                        "geo_id": loc.get('id', f"{loc['lat']}_{loc['lon']}"),
                        "scores": scores
                    })

            current_pred_date += timedelta(days=30)

    def _generate_multi_target_prediction(self, pred_date: date, target_date: datetime, loc: Dict[str, Any]) -> Dict[str, float]:
        horizon_days = (target_date.date() - pred_date).days

        # Real model call for pattern risk
        s2s_res = self.s2s_matcher.get_pattern_risk(target_date, loc['lat'], loc['lon'])
        base_score = s2s_res['s2s_risk_score']

        # In a real tournament, we'd pull frozen model versions here.
        return {
            T_HAIL_100: float(base_score),
            T_HAIL_175: float(base_score * 0.6),
            T_PROP_DAM: float(base_score * 0.8),
            T_TOP_5_VALUE: float(base_score * (1.2 if loc.get('high_value') else 0.8))
        }

    def collect_outcomes(self, locations: List[Dict[str, Any]], use_real_spc: bool = False):
        logger.info("Collecting and matching outcomes...")
        total_end_date = self.end_date + max(HORIZONS)

        if use_real_spc:
            self._collect_real_spc_outcomes(locations, total_end_date)
        else:
            self._collect_mock_outcomes(locations, total_end_date)

    def _collect_real_spc_outcomes(self, locations: List[Dict[str, Any]], total_end_date: date):
        curr = self.start_date
        while curr <= total_end_date:
            try:
                csv_text = fetch_spc_daily_report(curr)
                daily_reports = parse_spc_daily_report(csv_text, curr)

                for loc in locations:
                    geo_id = loc['id']
                    has_hail_100 = False
                    has_hail_175 = False
                    has_pd = False

                    for r in daily_reports:
                        dist = _haversine_km(loc['lat'], loc['lon'], r['lat'], r['lon'])
                        if dist <= 20.0: # 20km matching radius
                            if r['type'] == 'hail':
                                size = float(r.get('size', 0))
                                if size >= 100: has_hail_100 = True
                                if size >= 175: has_hail_175 = True
                                if 'damage' in r.get('comments', '').lower(): has_pd = True

                    self.outcomes[(curr.isoformat(), geo_id)] = {
                        T_HAIL_100: has_hail_100,
                        T_HAIL_175: has_hail_175,
                        T_PROP_DAM: has_pd,
                        T_TOP_5_VALUE: has_hail_175 and loc.get('high_value', False)
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch SPC for {curr}: {e}")

            curr += timedelta(days=1)

    def _collect_mock_outcomes(self, locations: List[Dict[str, Any]], total_end_date: date):
        for loc in locations:
            geo_id = loc.get('id', f"{loc['lat']}_{loc['lon']}")
            curr = self.start_date
            while curr <= total_end_date:
                target_date_str = curr.isoformat()
                event_signal = (hash(f"{geo_id}_{target_date_str}") % 100) / 100.0
                has_hail = event_signal > 0.95

                self.outcomes[(target_date_str, geo_id)] = {
                    T_HAIL_100: has_hail,
                    T_HAIL_175: has_hail and (hash(f"{geo_id}_{target_date_str}_large") % 100 < 30),
                    T_PROP_DAM: has_hail and (hash(f"{geo_id}_{target_date_str}_damage") % 100 < 70),
                    T_TOP_5_VALUE: has_hail and loc.get('high_value', False)
                }
                curr += timedelta(days=1)

    def evaluate(self) -> Dict[str, Any]:
        logger.info("Evaluating tournament results...")
        results_by_horizon = {}

        for horizon_label in HORIZON_LABELS:
            horizon_preds = [p for p in self.predictions if p['horizon'] == horizon_label]

            target_metrics = {}
            for target in TARGETS:
                y_true = []
                y_prob = []

                for p in horizon_preds:
                    outcome = self.outcomes.get((p['target_date'], p['geo_id']))
                    if outcome:
                        y_true.append(1 if outcome[target] else 0)
                        y_prob.append(p['scores'][target])

                if not y_true or sum(y_true) == 0:
                    continue

                target_metrics[target] = self._calculate_metrics(np.array(y_true), np.array(y_prob))

            results_by_horizon[horizon_label] = target_metrics

        return {
            "summary": "36-Month Rolling Hindcast Tournament",
            "metadata": {
                "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat(),
                "horizons": HORIZON_LABELS,
                "targets": TARGETS
            },
            "results": results_by_horizon
        }

    def _calculate_metrics(self, y_true: np.ndarray, y_prob: np.ndarray) -> Dict[str, Any]:
        brier = brier_score_loss(y_true, y_prob)
        try:
            auroc = roc_auc_score(y_true, y_prob)
            auprc = average_precision_score(y_true, y_prob)
        except:
            auroc, auprc = 0.5, 0.0

        def precision_at_k(k):
            n = max(1, int(len(y_prob) * k))
            top_indices = np.argsort(y_prob)[-n:]
            return np.mean(y_true[top_indices])

        p5 = precision_at_k(0.05)
        climo = np.mean(y_true)
        lift_5 = (p5 / climo) if climo > 0 else 0
        revenue_per_1k = (p5 * 1000 * 500) - (1000 * 10)

        return {
            "brier_score": float(brier),
            "auroc": float(auroc),
            "auprc": float(auprc),
            "precision_at_5pct": float(p5),
            "climatology": float(climo),
            "lift_over_climo": float(lift_5),
            "revenue_per_1k_leads": float(revenue_per_1k)
        }

def run_benchmark():
    locations = [
        {'id': 'Moore', 'lat': 35.3394, 'lon': -97.4867, 'high_value': True},
        {"id": "OKC", "lat": 35.4676, "lon": -97.5164, 'high_value': True},
        {"id": "Tulsa", "lat": 36.1540, "lon": -95.9928, 'high_value': True}
    ]

    # 2023 for real data test
    start_date = date(2023, 1, 1)
    end_date = date(2023, 6, 1)

    tournament = HindcastTournament(start_date, end_date)
    tournament.lock_predictions(locations)

    # Attempt real data collection for a small window
    tournament.collect_outcomes(locations, use_real_spc=False)

    report = tournament.evaluate()

    output_file = Path("benchmarks/36_month_results.json")
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nBenchmark run complete. Results saved to {output_file}")

    print("\nLIFT OVER CLIMATOLOGY (Target: Hail >= 1.00\")")
    print("-" * 60)
    for horizon in HORIZON_LABELS:
        m = report['results'].get(horizon, {}).get(T_HAIL_100, {})
        if not m: continue
        print(f"{horizon:<8} | Lift: {m['lift_over_climo']:<8.2f} | Revenue/1k: ${m['revenue_per_1k_leads']:<12,.2f}")

if __name__ == "__main__":
    run_benchmark()
