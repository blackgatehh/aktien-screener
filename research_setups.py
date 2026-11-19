"""Forschung: Welche Short- (und Long-) Setups erreichen ihr Ziel mit ≥ 55–60 % Wahrscheinlichkeit?

Getestet werden verschiedene Setup-Typen, Einstieg zum Eröffnungskurs am Folgetag, Stop je Setup,
Ziele in Vielfachen des Risikos (R) sowie feste Kursrückgänge (−5/−10 %). Zeithorizont 15 Handelstage
(ca. 3 Wochen, passend zu Knock-out-Trades) und zusätzlich 30 Tage.

Ausgabe: data/research_setups.md und data/research_signals.csv.gz
Aufruf:  python research_setups.py [6y]
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

import chart
from backtest import download
from universe import INDEX_BENCHMARK, benchmark_for, load_universe

DATA = os.path.join(os.path.dirname(__file__), "data")
HORIZONS = (15, 30)


def signals(t_name: str, df: pd.DataFrame, bench: pd.DataFrame | None) -> list[dict]:
    f = chart.chart_frame(df)
    o, h, l, c = (f[k].values for k in ("open", "high", "low", "close"))
    v = df["Volume"].values.astype(float)
    a = f["atr"].values
    e5, e20, e50, e200 = (f[f"ema{n}"].values for n in (5, 20, 50, 200))
    sl200, rsi2, stack = f["slope200"].values, f["rsi2"].values, f["stack"].values
    x50 = f["x50_200"].values
    ret126 = f["ret126"].values
    bside = chart.bench_side_series(bench, f.index).values
    bret = chart.bench_ret_series(bench, f.index).values
    vavg = pd.Series(v).rolling(50).mean().shift(1).values
    low20 = pd.Series(l).rolling(20).min().shift(1).values
    high20 = pd.Series(h).rolling(20).max().shift(1).values
    n = len(f)
    out = []
    down = (c < e200) & (e50 < e200) & (sl200 < 0)
    up = (c > e200) & (e50 > e200) & (sl200 > 0)
    for t in range(260, n - 2):
        if not np.isfinite(a[t]) or a[t] <= 0:
            continue
        cand = []
        # ---------------- Short-Setups
        if down[t]:
            # A: Abprall an EMA 20/50 von unten (Rally in den Abwärtstrend), rote Kerze
            if e20[t] < e50[t] and h[t] >= min(e20[t], e50[t]) and c[t] < e20[t] and c[t] < o[t]:
                cand.append(("S_ema_abprall", -1, max(h[t], h[t - 1]) + 0.25 * a[t]))
            # B: Bruch des 20-Tage-Tiefs mit Volumen
            if c[t] < low20[t] and np.isfinite(vavg[t]) and v[t] > 1.5 * vavg[t]:
                cand.append(("S_breakdown", -1, c[t] + 1.5 * a[t]))
            # D: frisches Death Cross (≤ 20 Tage) und Ablehnung an der EMA 50
            if np.isfinite(x50[t]) and -20 <= x50[t] < 0 and h[t] >= e50[t] > c[t]:
                cand.append(("S_deathcross_ema50", -1, h[t] + 0.25 * a[t]))
            # E: kurzfristig überkauft im Abwärtstrend
            if rsi2[t] > 90:
                cand.append(("S_rsi2_ueberkauft", -1, h[t] + 1.0 * a[t]))
        # C: Gap nach unten ≥ 4 %, gehalten, hohes Volumen (Drift nach schlechten News/Zahlen)
        if o[t] < l[t - 1] * 0.96 and c[t] <= (o[t] + l[t - 1]) / 2 and np.isfinite(vavg[t]) and v[t] > 2 * vavg[t]:
            cand.append(("S_gap_down", -1, h[t] + 0.25 * a[t]))
        # ---------------- Long-Gegenstücke (zum Vergleich)
        if up[t]:
            if e20[t] > e50[t] and l[t] <= max(e20[t], e50[t]) and c[t] > e20[t] and c[t] > o[t]:
                cand.append(("L_ema_abprall", 1, min(l[t], l[t - 1]) - 0.25 * a[t]))
            if c[t] > high20[t] and np.isfinite(vavg[t]) and v[t] > 1.5 * vavg[t]:
                cand.append(("L_breakout", 1, c[t] - 1.5 * a[t]))
            if rsi2[t] < 10:
                cand.append(("L_rsi2_ueberverkauft", 1, l[t] - 1.0 * a[t]))
        if o[t] > h[t - 1] * 1.04 and c[t] >= (o[t] + h[t - 1]) / 2 and np.isfinite(vavg[t]) and v[t] > 2 * vavg[t]:
            cand.append(("L_gap_up", 1, l[t] - 0.25 * a[t]))

        for name, s, stop in cand:
            entry = o[t + 1]
            risk = (entry - stop) * s
            if risk <= 0 or risk / entry > 0.15:
                continue
            row = {"ticker": t_name, "date": f.index[t].strftime("%Y-%m-%d"), "setup": name, "dir": s,
                   "risk_pct": risk / entry * 100, "atr_pct": a[t] / c[t] * 100,
                   "stack": s * stack[t] / 4, "bench_aligned": s * bside[t],
                   "rs126": s * ((ret126[t] if np.isfinite(ret126[t]) else 0) - bret[t]),
                   "rsi2": rsi2[t], "vol_ratio": v[t] / vavg[t] if np.isfinite(vavg[t]) and vavg[t] > 0 else np.nan}
            for H in HORIZONS:
                end = min(n, t + 1 + H)
                if end - (t + 1) < H:
                    break
                mfe, stopped, mx = 0.0, False, 0.0
                for j in range(t + 1, end):
                    if (s > 0 and l[j] <= stop) or (s < 0 and h[j] >= stop):
                        stopped = True
                        break
                    fav = ((h[j] - entry) if s > 0 else (entry - l[j])) / risk
                    mfe = max(mfe, fav)
                    mx = max(mx, ((h[j] / entry - 1) if s > 0 else (1 - l[j] / entry)) * 100)
                row[f"mfe{H}"] = mfe
                row[f"move{H}"] = mx  # größte Bewegung in % zugunsten des Trades vor dem Stop
                row[f"ret{H}"] = (c[end - 1] / entry - 1) * 100 * s
            else:
                out.append(row)
    return out


def table(d: pd.DataFrame, by: str) -> pd.DataFrame:
    rows = []
    for k, g in d.groupby(by, observed=True):
        te = g[g["date"] >= TEST_FROM]
        r = {by: k, "n": len(g), "n_test": len(te)}
        for R in (0.5, 1, 1.5, 2):
            r[f"P {R}R"] = round((g["mfe15"] >= R).mean() * 100, 1)
        r["P 1R Test"] = round((te["mfe15"] >= 1).mean() * 100, 1) if len(te) else np.nan
        r["P −5 %"] = round((g["move15"] >= 5).mean() * 100, 1)
        r["P −10 %"] = round((g["move15"] >= 10).mean() * 100, 1)
        r["P 1R (30T)"] = round((g["mfe30"] >= 1).mean() * 100, 1)
        r["Stop Ø %"] = round(g["risk_pct"].mean(), 1)
        rows.append(r)
    return pd.DataFrame(rows).set_index(by)


TEST_FROM = "2025-11-17"

if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else "6y"
    uni = load_universe()
    prices = download(uni["ticker"].tolist() + sorted(set(INDEX_BENCHMARK.values())), period)
    rows, t0 = [], time.time()
    for k, (_, u) in enumerate(uni.iterrows()):
        df = prices.get(u["ticker"])
        if df is None:
            continue
        try:
            rows += signals(u["ticker"], df, prices.get(benchmark_for(u["indices"])))
        except Exception as exc:  # noqa: BLE001
            print(f"[{u['ticker']}] {exc}")
        if k % 100 == 99:
            print(f"{k + 1}/{len(uni)} · {len(rows)} · {time.time() - t0:.0f}s")
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(DATA, "research_signals.csv.gz"), index=False, compression="gzip")
    d["jahr"] = d["date"].str[:4]
    lines = [f"# Setup-Forschung · {len(d):,} Signale · Ziel/Stop innerhalb von 15 Handelstagen", "",
             "P xR = Ziel (x × Risiko) vor dem Stop erreicht. P −5/−10 % = Kurs fällt (Short) bzw. steigt (Long) "
             "mindestens so weit, bevor der Stop fällt. Test = ab " + TEST_FROM + ".", "",
             "## Alle Setups", "", table(d, "setup").to_markdown(), ""]
    for nm in sorted(d["setup"].unique()):
        g = d[d["setup"] == nm]
        lines += [f"## {nm}", "", "Nach Jahr:", "", table(g, "jahr").to_markdown(), "",
                  "Index über/unter EMA 200 (in Tradingrichtung +1 = Rückenwind):", "", table(g, "bench_aligned").to_markdown(), "",
                  "EMA-Fächer in Tradingrichtung:", "",
                  table(g.assign(f=pd.cut(g["stack"], [-1.01, 0, 0.5, 0.99, 1.01],
                                          labels=["dagegen", "neutral", "eher dafür", "voll dafür"])), "f").to_markdown(), "",
                  "Relative Stärke 6 M in Tradingrichtung (Pp):", "",
                  table(g.assign(r=pd.cut(g["rs126"], [-999, -10, 0, 10, 25, 999])), "r").to_markdown(), ""]
    with open(os.path.join(DATA, "research_setups.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines[:12]))
