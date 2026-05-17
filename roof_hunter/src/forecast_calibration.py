"""
Probabilistic forecast calibration scoring.

Useful when a roof-hunter component (e.g. simulator.py's Lagrangian Monte
Carlo, ml_models.predict_hail_xgboost, satellite_nowcast_engine,
RoofHunterWeatherTwin) emits a *probability* of an outcome (e.g.
P(hail diameter > 1 inch within next hour at this lat/lon)) rather than a
deterministic prediction.

Standard precision / recall / F1 evaluate whether the *thresholded*
prediction is right; they do NOT tell you whether the probabilities
themselves are calibrated. A model that says "90% chance of hail" should
actually produce hail in 90% of similar situations. If it produces hail
60% of the time, the model is over-confident and you cannot use the
probabilities as-is for Bayesian fusion, downstream cost / loss math, or
adjusting outbound-call sizing.

Three metrics are exported:

  * Brier score        — mean squared error between probabilities and
                         observed 0/1 outcome. Lower is better. 0.0 = perfect.
  * NLL (log-loss)     — mean negative log-probability assigned to the
                         realised outcome. Lower is better. ∞ = a confident
                         wrong prediction.
  * Reliability table  — bins predicted-probability into deciles (or
                         user-chosen edges) and reports observed frequency
                         per bin. Use this for reliability diagrams and to
                         estimate the empirical bias correction needed.

All three accept the same input shape and have no external dependencies
beyond the stdlib.

Example: scoring simulator.py's P(D>1in) over a 12-month backtest

    from src.forecast_calibration import binary_brier, binary_nll, reliability_table

    probs    = []   # P(D>1in) returned by simulator.run_from_forecast_row
    outcomes = []   # 1 if NOAA Storm Events confirmed >=1in hail in the
                    # space-time match window, 0 otherwise

    for forecast_row, ground_truth in pairs:
        out = simulator.run_from_forecast_row(forecast_row, n_iterations=2000)
        probs.append(out["damage_probability_gt_1in"])
        outcomes.append(int(ground_truth.confirmed_hail_gt_1in))

    print("Brier:", binary_brier(probs, outcomes))
    print("NLL  :", binary_nll(probs, outcomes))
    for bin_lo, bin_hi, n, mean_pred, freq in reliability_table(probs, outcomes):
        print(f"  [{bin_lo:.2f},{bin_hi:.2f})  n={n:3d}  pred≈{mean_pred:.3f}  obs≈{freq:.3f}")
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def _validate_pairs(probs, outcomes) -> tuple[list[float], list[int]]:
    if len(probs) != len(outcomes):
        raise ValueError(f"length mismatch: probs={len(probs)} outcomes={len(outcomes)}")
    p_clean: list[float] = []
    y_clean: list[int] = []
    for p, y in zip(probs, outcomes):
        if p is None or y is None:
            continue
        p = float(p)
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"probability out of [0,1]: {p}")
        if int(y) not in (0, 1):
            raise ValueError(f"binary outcome must be 0/1, got {y}")
        p_clean.append(p)
        y_clean.append(int(y))
    if not p_clean:
        raise ValueError("no usable (probability, outcome) pairs")
    return p_clean, y_clean


def binary_brier(probs, outcomes) -> float:
    """Brier score for binary outcomes: mean((p - y)^2)."""
    p, y = _validate_pairs(probs, outcomes)
    return sum((pi - yi) ** 2 for pi, yi in zip(p, y)) / len(p)


def binary_nll(probs, outcomes, eps: float = 1e-12) -> float:
    """Mean negative log-likelihood (log-loss) for binary outcomes."""
    p, y = _validate_pairs(probs, outcomes)
    total = 0.0
    for pi, yi in zip(p, y):
        pi_c = min(max(pi, eps), 1.0 - eps)
        total += -(yi * math.log(pi_c) + (1 - yi) * math.log(1.0 - pi_c))
    return total / len(p)


@dataclass
class ReliabilityBin:
    lo: float
    hi: float
    n: int
    mean_predicted: float
    observed_frequency: float

    def calibration_gap(self) -> float:
        """Positive => model under-predicts in this bin; negative => over-predicts."""
        return self.observed_frequency - self.mean_predicted


def reliability_table(
    probs,
    outcomes,
    bin_edges: list[float] | None = None,
) -> list[ReliabilityBin]:
    """
    Bin predicted probabilities and report (mean predicted prob, observed
    frequency, n) per bin. Default = deciles 0.0..1.0 in 0.1 increments.

    Reading the output:
      observed_frequency >> mean_predicted  => model under-predicts here
      observed_frequency << mean_predicted  => model over-predicts here
      perfectly calibrated                   => observed ≈ mean_predicted
    """
    p, y = _validate_pairs(probs, outcomes)
    if bin_edges is None:
        bin_edges = [round(i * 0.1, 4) for i in range(11)]
    if bin_edges[0] != 0.0 or bin_edges[-1] != 1.0:
        raise ValueError("bin_edges must start at 0.0 and end at 1.0")
    if any(b <= a for a, b in zip(bin_edges[:-1], bin_edges[1:])):
        raise ValueError("bin_edges must be strictly increasing")

    n_bins = len(bin_edges) - 1
    counts = [0] * n_bins
    pred_sum = [0.0] * n_bins
    obs_sum = [0] * n_bins
    for pi, yi in zip(p, y):
        if pi == 1.0:
            idx = n_bins - 1
        else:
            idx = 0
            for k in range(n_bins):
                if bin_edges[k] <= pi < bin_edges[k + 1]:
                    idx = k
                    break
        counts[idx] += 1
        pred_sum[idx] += pi
        obs_sum[idx] += yi

    out: list[ReliabilityBin] = []
    for k in range(n_bins):
        n = counts[k]
        out.append(
            ReliabilityBin(
                lo=bin_edges[k],
                hi=bin_edges[k + 1],
                n=n,
                mean_predicted=pred_sum[k] / n if n else float("nan"),
                observed_frequency=obs_sum[k] / n if n else float("nan"),
            )
        )
    return out


def expected_calibration_error(
    probs,
    outcomes,
    bin_edges: list[float] | None = None,
) -> float:
    """
    ECE: weighted average |observed - predicted| across reliability bins.
    A common single-number summary of miscalibration. Closer to 0 = better.
    """
    table = reliability_table(probs, outcomes, bin_edges)
    total_n = sum(b.n for b in table)
    if total_n == 0:
        return 0.0
    return sum((b.n / total_n) * abs(b.calibration_gap()) for b in table if b.n)


def calibration_summary(
    probs,
    outcomes,
    label: str = "",
    bin_edges: list[float] | None = None,
) -> str:
    """One-shot human-readable calibration report."""
    n = sum(1 for p, y in zip(probs, outcomes) if p is not None and y is not None)
    brier = binary_brier(probs, outcomes)
    nll = binary_nll(probs, outcomes)
    ece = expected_calibration_error(probs, outcomes, bin_edges)
    table = reliability_table(probs, outcomes, bin_edges)
    lines = [
        f"Calibration report{(' — ' + label) if label else ''}",
        f"  n={n}  Brier={brier:.4f}  NLL={nll:.4f}  ECE={ece:.4f}",
        f"  bin                 n     pred     obs      gap",
    ]
    for b in table:
        if b.n == 0:
            continue
        lines.append(
            f"  [{b.lo:.2f},{b.hi:.2f})  {b.n:5d}  {b.mean_predicted:6.3f}  "
            f"{b.observed_frequency:6.3f}  {b.calibration_gap():+6.3f}"
        )
    return "\n".join(lines)


__all__ = [
    "binary_brier",
    "binary_nll",
    "reliability_table",
    "expected_calibration_error",
    "calibration_summary",
    "ReliabilityBin",
]
