"""Big-Move-Modell: Welche Aktien steigen (fallen) in 3–6 Wochen um 10/15/20 %, bevor der Stop fällt?

Für jede Aktie und jeden Handelstag (jeden 2. Tag) werden Chart-Merkmale berechnet und gezählt, ob
ab Eröffnung des Folgetags innerhalb von 30 Handelstagen ein Kursziel von +10 % (+15 %, +20 %) bzw.
−10 % (−15 %) erreicht wird, BEVOR ein Stop fällt. Stop = 2 × ATR, mindestens 5 %, höchstens 10 %.

Modell: Gradient Boosting je Richtung (sklearn HistGradientBoostingClassifier), Ziel +10 % bzw. −10 %.
Bewertung außerhalb der Trainingszeit: Wie oft erreichen die 10 bestbewerteten Aktien eines Tages das Ziel?

Aufruf:
    python bigmove.py research [6y]   Daten laden, Modell trainieren, Bericht + Modell schreiben
Ausgabe in data/: bigmove_model.pkl, bigmove_report.md, bigmove_meta.json
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import chart

DATA = os.path.join(os.path.dirname(__file__), "data")
H = 30                       # Handelstage (ca. 6 Wochen)
TARGETS = (10, 15, 20)
GAP = 35                     # Abstand Training/Test in Kalendertagen (keine Überlappung der Zeitfenster)

FEATS = ["atr_pct", "ret5", "ret20", "ret60", "ret126", "ret252", "rs20", "rs60", "rs126", "d_hi252", "d_lo252",
         "stack", "slope200", "slope50", "d200_atr", "d50_atr", "d20_atr", "x5_13", "x20_50", "x50_200", "rsi", "rsi2",
         "vol5_50", "vol1_50", "gap_up20", "gap_dn20", "range20_atr", "range60_atr", "close_pos", "updays10",
         "bench_side", "bench_ret20", "hi_new20", "lo_new20", "dist_ema20_pct"]


def frame(df: pd.DataFrame, bench: pd.DataFrame | None) -> pd.DataFrame:
    """Merkmale je Tag (nur Vergangenheit)."""
    f = chart.chart_frame(df)
    c, h, l, o = f["close"], f["high"], f["low"], f["open"]
    v = df["Volume"].astype(float).reindex(f.index)
    a = f["atr"]
    x = pd.DataFrame(index=f.index)
    x["atr_pct"] = a / c * 100
    for n in (5, 20, 60, 126, 252):
        x[f"ret{n}"] = (c / c.shift(n) - 1) * 100
    if bench is not None and len(bench) > 260:
        bc = bench["Close"].reindex(f.index, method="ffill")
        for n in (20, 60, 126):
            x[f"rs{n}"] = x[f"ret{n}"] - (bc / bc.shift(n) - 1) * 100
        x["bench_side"] = np.sign(bc - bc.ewm(span=200, adjust=False).mean())
        x["bench_ret20"] = (bc / bc.shift(20) - 1) * 100
    else:
        for k in ("rs20", "rs60", "rs126", "bench_side", "bench_ret20"):
            x[k] = 0.0
    x["d_hi252"] = (c / h.rolling(252, min_periods=120).max() - 1) * 100
    x["d_lo252"] = (c / l.rolling(252, min_periods=120).min() - 1) * 100
    for k in ("stack", "slope200", "slope50", "d200_atr", "d50_atr", "x5_13", "x20_50", "x50_200", "rsi", "rsi2"):
        x[k] = f[k]
    x["d20_atr"] = (c - f["ema20"]) / a
    x["dist_ema20_pct"] = (c / f["ema20"] - 1) * 100
    va = v.rolling(50).mean().shift(1)
    x["vol5_50"] = v.rolling(5).mean() / va
    x["vol1_50"] = v / va
    gap = (o / c.shift(1) - 1) * 100
    x["gap_up20"] = gap.clip(lower=0).rolling(20).max()
    x["gap_dn20"] = (-gap).clip(lower=0).rolling(20).max()
    x["range20_atr"] = (h.rolling(20).max() - l.rolling(20).min()) / a
    x["range60_atr"] = (h.rolling(60).max() - l.rolling(60).min()) / a
    rng = (h - l).replace(0, np.nan)
    x["close_pos"] = (c - l) / rng
    x["updays10"] = (c.diff() > 0).rolling(10).sum()
    x["hi_new20"] = (h >= h.rolling(20).max()).astype(float).rolling(5).sum()
    x["lo_new20"] = (l <= l.rolling(20).min()).astype(float).rolling(5).sum()
    return x.replace([np.inf, -np.inf], np.nan)


def labels(df: pd.DataFrame, atr_pct: np.ndarray) -> dict[str, np.ndarray]:
    """Ziel vor Stop innerhalb von H Tagen, Einstieg = Eröffnung Folgetag."""
    o, h, l = (df[k].values.astype(float) for k in ("Open", "High", "Low"))
    n = len(o)
    out = {f"up{p}": np.full(n, np.nan) for p in TARGETS}
    out.update({f"dn{p}": np.full(n, np.nan) for p in TARGETS})
    out["maxup"], out["maxdn"] = np.full(n, np.nan), np.full(n, np.nan)
    for t in range(n - H - 1):
        e = o[t + 1]
        if not np.isfinite(e) or e <= 0 or not np.isfinite(atr_pct[t]):
            continue
        s = float(np.clip(2 * atr_pct[t], 5, 10)) / 100
        hh, ll = h[t + 1:t + 1 + H], l[t + 1:t + 1 + H]
        # Long: Stop unten
        stop_l = np.argmax(ll <= e * (1 - s)) if (ll <= e * (1 - s)).any() else H
        stop_s = np.argmax(hh >= e * (1 + s)) if (hh >= e * (1 + s)).any() else H
        for p in TARGETS:
            hit = hh >= e * (1 + p / 100)
            i = np.argmax(hit) if hit.any() else H
            out[f"up{p}"][t] = float(i < H and i < stop_l)          # gleicher Tag zählt als Stop
            hit = ll <= e * (1 - p / 100)
            i = np.argmax(hit) if hit.any() else H
            out[f"dn{p}"][t] = float(i < H and i < stop_s)
        out["maxup"][t] = (hh.max() / e - 1) * 100
        out["maxdn"][t] = (1 - ll.min() / e) * 100
    return out


def build(prices: dict, uni: pd.DataFrame, step: int = 2) -> pd.DataFrame:
    from universe import benchmark_for

    parts, t0 = [], time.time()
    for k, (_, u) in enumerate(uni.iterrows()):
        df = prices.get(u["ticker"])
        if df is None or len(df) < 400:
            continue
        try:
            x = frame(df, prices.get(benchmark_for(u["indices"])))
            lab = labels(df, x["atr_pct"].values)
            for key, arr in lab.items():
                x[key] = arr
            x["ticker"] = u["ticker"]
            x = x.iloc[260::step].dropna(subset=["up10", "ret252"])
            parts.append(x.reset_index(names="date"))
        except Exception as exc:  # noqa: BLE001
            print(f"[{u['ticker']}] {exc}")
        if k % 100 == 99:
            print(f"{k + 1}/{len(uni)} · {time.time() - t0:.0f}s")
    d = pd.concat(parts, ignore_index=True)
    d["date"] = pd.to_datetime(d["date"])
    for col in FEATS:
        d[col] = d[col].astype("float32")
    return d


def precision_at_k(d: pd.DataFrame, p: np.ndarray, y: str, k: int = 10) -> tuple[float, float]:
    t = d[["date", y]].assign(p=p)
    top = t.sort_values("p", ascending=False).groupby("date").head(k)
    return float(top[y].mean()), float(t[y].mean())


def research(period: str) -> None:
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score

    from backtest import download
    from universe import INDEX_BENCHMARK, load_universe

    uni = load_universe()
    prices = download(uni["ticker"].tolist() + sorted(set(INDEX_BENCHMARK.values())), period)
    d = build(prices, uni)
    last = d["date"].max()
    test_from = last - pd.Timedelta(days=365)
    tr = d[d["date"] < test_from - pd.Timedelta(days=GAP)]
    te = d[d["date"] >= test_from]
    lines = [f"# Big-Move-Modell · {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", "",
             f"{d['ticker'].nunique()} Aktien, {len(d):,} Aktien-Tage (jeder 2. Tag), Horizont {H} Handelstage, "
             f"Stop 2 × ATR (5–10 %). Training bis {tr['date'].max():%d.%m.%Y}, Test ab {test_from:%d.%m.%Y} "
             f"({len(te):,} Aktien-Tage).", "",
             "## Basisquoten (alle Aktien-Tage)", "",
             "| Ziel vor Stop | Long | Short |", "|---|---|---|"]
    for p in TARGETS:
        lines.append(f"| {p} % | {d[f'up{p}'].mean() * 100:.1f} % | {d[f'dn{p}'].mean() * 100:.1f} % |")
    models, meta = {}, {"features": FEATS, "horizon": H, "generated_utc": f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M}"}
    lines += ["", "## Modell außerhalb der Trainingszeit", "",
              "Top 10 = die 10 Aktien mit der höchsten vorhergesagten Wahrscheinlichkeit je Tag.", "",
              "| Richtung · Ziel | AUC | Top 10 je Tag | Top 3 je Tag | Basis | Faktor |", "|---|---|---|---|---|---|"]
    for side, y in (("long", "up10"), ("short", "dn10")):
        m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                           min_samples_leaf=400, l2_regularization=1.0, random_state=7)
        m.fit(tr[FEATS], tr[y])
        p = m.predict_proba(te[FEATS])[:, 1]
        auc = roc_auc_score(te[y], p)
        p10, base = precision_at_k(te, p, y, 10)
        p3, _ = precision_at_k(te, p, y, 3)
        lines.append(f"| {side} · {y[2:]} % | {auc:.3f} | {p10 * 100:.1f} % | {p3 * 100:.1f} % | {base * 100:.1f} % | "
                     f"{p10 / base:.1f}× |")
        # Kalibrierung: vorhergesagt vs. eingetreten
        cal = te[[y]].assign(p=p)
        cal["bin"] = pd.qcut(cal["p"], 10, duplicates="drop")
        ct = cal.groupby("bin", observed=True).agg(vorhergesagt=("p", "mean"), eingetreten=(y, "mean"), n=(y, "size"))
        meta[f"{side}_calib"] = {"pred": ct["vorhergesagt"].round(4).tolist(), "obs": ct["eingetreten"].round(4).tolist()}
        meta[f"{side}_test"] = {"auc": auc, "top10": p10, "top3": p3, "base": base}
        # Andere Ziele mit demselben Ranking
        for q in TARGETS[1:]:
            yy = f"{y[:2]}{q}"
            pq, bq = precision_at_k(te, p, yy, 10)
            meta[f"{side}_test"][f"top10_{q}"] = pq
            meta[f"{side}_test"][f"base_{q}"] = bq
        # Produktivmodell auf allen Daten
        mf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                            min_samples_leaf=400, l2_regularization=1.0, random_state=7)
        mf.fit(d[d["date"] <= last - pd.Timedelta(days=45)][FEATS], d[d["date"] <= last - pd.Timedelta(days=45)][y])
        models[side] = mf
        lines += ["", f"### {side} · Kalibrierung (Test, Zehntel nach Vorhersage)", "", ct.round(3).to_markdown(), ""]
        # Was die Top-Auswahl ausmacht: Mittelwerte der Merkmale Top-10 vs. alle
        t = te.assign(p=p)
        top = t.sort_values("p", ascending=False).groupby("date").head(10)
        prof = pd.DataFrame({"Top 10": top[FEATS].median(), "alle": t[FEATS].median()}).round(2)
        lines += [f"### {side} · typisches Profil der Top 10 (Median)", "", prof.to_markdown(), ""]
    lines += ["## Weitere Ziele mit demselben Ranking (Test, Top 10 je Tag)", "", "| | Top 10 | Basis |", "|---|---|---|"]
    for side, pre in (("long", "+"), ("short", "−")):
        for q in TARGETS[1:]:
            mt = meta[f"{side}_test"]
            lines.append(f"| {side} {pre}{q} % | {mt[f'top10_{q}'] * 100:.1f} % | {mt[f'base_{q}'] * 100:.1f} % |")
    lines += ["", "Hinweis: heutiges Index-Universum (Survivorship Bias), keine Kosten. Ziel und Stop am selben Tag zählen als Stop."]
    with open(os.path.join(DATA, "bigmove_model.pkl"), "wb") as fh:
        pickle.dump(models, fh)
    with open(os.path.join(DATA, "bigmove_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, default=float)
    with open(os.path.join(DATA, "bigmove_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines[:30]))


# ----------------------------------------------------------------- Live
def load_models():
    path = os.path.join(DATA, "bigmove_model.pkl")
    if not os.path.exists(path):
        return None, None
    with open(path, "rb") as fh:
        models = pickle.load(fh)
    with open(os.path.join(DATA, "bigmove_meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    return models, meta


def score_live(df: pd.DataFrame, bench: pd.DataFrame | None, models: dict) -> dict:
    """Wahrscheinlichkeiten für heute und die letzten 5 Tage (für die Beständigkeit)."""
    x = frame(df, bench).tail(5)
    out = {}
    for side, m in models.items():
        p = m.predict_proba(x[FEATS])[:, 1]
        out[f"bm_{side}"] = float(p[-1])
        out[f"bm_{side}_avg3"] = float(np.mean(p[-3:]))
        out[f"bm_{side}_min5"] = float(np.min(p))
    out["bm_atr_pct"] = float(x["atr_pct"].iloc[-1])
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "research":
        research(sys.argv[2] if len(sys.argv) > 2 else "6y")
