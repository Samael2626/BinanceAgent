"""Ad-hoc experiment: isolate the exit structure as the cause of negative edge.
Same entries (real strategy), vary only the exits. Pooled over 8 symbols, base costs."""
import pandas as pd
from harness import data_loader, engine, metrics
from harness.costs import CostModel

cm = CostModel.base()
SY = data_loader.SYMBOLS

# cache prepared arrays per (symbol, settings-signature) is overkill; re-prepare per variant
def run(settings, label):
    res = []
    for s in SY:
        arr = engine.to_arrays(engine.prepare(data_loader.load(s), settings))
        tr, cv = engine.run_strategy(arr, s, settings, cm, 1000.0, 12.0)
        res.append((tr, cv))
    trades = [t for tr, _ in res for t in tr]
    series = []
    for _, cv in res:
        sx = pd.Series({p["time"]: p["equity"] for p in cv})
        sx.index = pd.to_datetime(sx.index, utc=True)
        series.append(sx.resample("1D").last().ffill())
    agg = pd.concat(series, axis=1).ffill().fillna(1000.0).sum(axis=1)
    curve = [{"time": t, "equity": float(v)} for t, v in agg.items()]
    m = metrics.compute(trades, curve, 1000.0 * len(SY))
    print(f"{label:44s} {m.row()}")

base = dict(engine.DEFAULT_SETTINGS)
print("EXIT VARIANTS (same entries, pooled 8 symbols, base costs):")
run(base, "A) actual: trail0.8 SL1.5 TP1.5")
v = dict(base); v["rsi_trailing_pct"] = 99.0
run(v, "B) no trailing: SL1.5 TP1.5")
v = dict(base); v["rsi_trailing_pct"] = 99.0; v["take_profit_pct"] = 3.0
run(v, "C) no trail, 2:1: SL1.5 TP3.0")
v = dict(base); v["rsi_trailing_pct"] = 99.0; v["take_profit_pct"] = 4.5
run(v, "D) no trail, 3:1: SL1.5 TP4.5")
