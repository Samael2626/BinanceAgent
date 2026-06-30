"""Regime windows and walk-forward splits (BTC-referenced, from the probe).

Regimes let us see if the edge survives outside bull markets. Walk-forward
test windows are consecutive forward slices; when we TUNE weights we fit on
the train portion and report only the unseen test portion (OOS).
"""
from __future__ import annotations

import pandas as pd

# (name, start, end)  -- inclusive start, exclusive end
REGIMES = [
    ("BULL_24Q4",   "2024-09-28", "2024-12-27"),
    ("LATERAL_25Q1", "2024-12-27", "2025-03-27"),
    ("BULL_25Q2",   "2025-03-27", "2025-06-25"),
    ("LATERAL_25Q3", "2025-06-25", "2025-09-23"),
    ("BEAR_25Q4",   "2025-09-23", "2025-12-22"),
    ("BEAR_26Q1",   "2025-12-22", "2026-03-22"),
    ("LATERAL_26Q2", "2026-03-22", "2026-06-20"),
]

# Out-of-sample split: TRAIN (tune weights here) | OOS (locked, never seen)
TRAIN_END = "2025-09-23"   # ~15 mo train (bull+lateral)
OOS_START = "2025-09-23"   # ~9 mo OOS (bear+lateral) -- the hard test


def idx_at(d: pd.DataFrame, date: str) -> int:
    """First row index with open_time >= date."""
    ts = pd.Timestamp(date, tz="UTC")
    mask = d["open_time"] >= ts
    if not mask.any():
        return len(d)
    return int(mask.idxmax())


def regime_bounds(d: pd.DataFrame):
    for name, a, b in REGIMES:
        yield name, idx_at(d, a), idx_at(d, b)


def train_oos_bounds(d: pd.DataFrame):
    return {
        "TRAIN": (idx_at(d, "2024-06-01"), idx_at(d, TRAIN_END)),
        "OOS": (idx_at(d, OOS_START), len(d)),
    }
