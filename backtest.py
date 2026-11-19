"""Backtest der Fibonacci-Setups und Schätzung der Gewinnwahrscheinlichkeit (Framework v3).

Frage: Wie oft erreicht ein Setup Ziel 1, bevor der Stop fällt?
Für jeden Titel und jeden Handelstag der letzten Jahre wird das Setup genau so bestimmt wie im
Live-Screener (chart.setup_at). Liegt der Kurs höchstens 5 % von der Zone entfernt, wird eine
Limit-Order in der Zone simuliert (Kurs in der Zone: Einstieg zum Schlusskurs, sonst Zonenmitte,
gültig 10 Tage). Danach zählt, was zuerst kommt: Stop oder Ziel 1 (maximal 60 Handelstage).

Ausgabe in data/:
    prob_model.json      logistisches Modell (Merkmale, Mittelwerte, Gewichte) + Kennzahlen
    backtest_report.md   Trefferquoten nach Trendklasse, EMA-Bild, Wahrscheinlichkeitsklassen
    backtest_signals.csv.gz  alle simulierten Signale (für spätere Auswertungen)

Bekannte Verzerrung: Das Universum ist das heutige (Survivorship Bias). Aus dem Index gefallene
Verlierer fehlen, Long-Trefferquoten sind daher eher etwas zu hoch.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import chart
from universe import INDEX_BENCHMARK, benchmark_for, load_universe

DATA = os.path.join(os.path.dirname(__file__), "data")
MAX_BARS, FILL_BARS, NEAR_PCT = 60, 10, 5.0


def simulate(f: pd.DataFrame, t: int, st: dict) -> dict | None:
    """Limit-Einstieg und Ausgang (Ziel 1 vor Stop) simulieren."""
    hi, lo, op, cl = (f[k].values for k in ("high", "low", "open", "close"))
    longs = st["setup"] == "long"
    stop, t1 = st["stop"], st["t1"]
    n = len(cl)
    if st["zone_dist_pct"] == 0:
        entry, fill = cl[t], t
    else:
        entry, fill = (st["zone_lo"] + st["zone_hi"]) / 2, None
        for j in range(t + 1, min(n, t + 1 + FILL_BARS)):
            if (longs and lo[j] <= entry) or (not longs and hi[j] >= entry):
                if (longs and op[j] < stop) or (not longs and op[j] > stop):
                    entry = op[j]  # Gap über den Stop hinweg: sofort ausgestoppt, unten verbucht
                fill = j
                break
        if fill is None:
            return {"filled": 0}
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    # Ab dem Füll-Tag selbst (bei Limit) bzw. ab dem Folgetag (bei Schlusskurs-Einstieg)
    start = fill if fill != t else t + 1
    for j in range(start, min(n, fill + 1 + MAX_BARS)):
        if longs:
            if lo[j] <= stop:
                px = min(op[j], stop) if j > fill else stop
                return {"filled": 1, "win": 0, "R": (px - entry) / risk, "bars": j - fill, "end": "stop"}
            if hi[j] >= t1:
                return {"filled": 1, "win": 1, "R": (t1 - entry) / risk, "bars": j - fill, "end": "t1"}
        else:
            if hi[j] >= stop:
                px = max(op[j], stop) if j > fill else stop
                return {"filled": 1, "win": 0, "R": (entry - px) / risk, "bars": j - fill, "end": "stop"}
            if lo[j] <= t1:
                return {"filled": 1, "win": 1, "R": (entry - t1) / risk, "bars": j - fill, "end": "t1"}
    j = min(n - 1, fill + MAX_BARS)
    if j - fill < MAX_BARS:  # noch offen (Daten enden) → nicht werten
        return None
    r = (cl[j] - entry) / risk * (1 if longs else -1)
    return {"filled": 1, "win": 0, "R": r, "bars": MAX_BARS, "end": "zeit"}


def signals_for(t_name: str, df: pd.DataFrame, bench: pd.DataFrame | None) -> list[dict]:
    f = chart.chart_frame(df)
    bside = chart.bench_side_series(bench, f.index).values
    out = []
    for t in range(260, len(f) - 1):
        st = chart.setup_at(f, t)
        if st is None or st["broken"] or abs(st["zone_dist_pct"]) > NEAR_PCT:
            continue
        # Nur Kurse in der Zone oder auf der Zielseite davor (Limit wartet in der Zone). Kurs schon zwischen
        # Zone und Stop: kein sauberes Setup mehr.
        if (st["setup"] == "long" and st["zone_dist_pct"] < 0) or (st["setup"] == "short" and st["zone_dist_pct"] > 0):
            continue
        res = simulate(f, t, st)
        if res is None:
            continue
        row = {"ticker": t_name, "date": f.index[t].strftime("%Y-%m-%d"), "setup": st["setup"],
               "key": f"{t_name}|{st['hi_idx']}|{st['lo_idx']}", "trend": chart.trend_class(f.iloc[t]),
               "stack_raw": float(f["stack"].values[t]), **res}
        if res.get("filled"):
            row.update(chart.features(f, t, st, bside[t]))
        out.append(row)
    return out


def download(tickers: list[str], period: str) -> dict[str, pd.DataFrame]:
    import yfinance as yf

    out = {}
    for i in range(0, len(tickers), 100):
        chunk = tickers[i:i + 100]
        for attempt in range(3):
            try:
                raw = yf.download(chunk, period=period, interval="1d", group_by="ticker", auto_adjust=True,
                                  threads=True, progress=False)
                break
            except Exception as exc:  # noqa: BLE001
                print(f"[download] {exc}")
                time.sleep(10 * (attempt + 1))
        else:
            continue
        for t in chunk:
            try:
                d = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
                d = d[["Open", "High", "Low", "Close", "Volume"]].dropna()
                if len(d) >= 400:
                    out[t] = d
            except KeyError:
                pass
        time.sleep(2)
    print(f"[download] {len(out)}/{len(tickers)}")
    return out


# ------------------------------------------------------------------- Modell
def fit(sig: pd.DataFrame, test_from: str) -> tuple[dict, pd.DataFrame]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import brier_score_loss, roc_auc_score

    X_cols = chart.FEATURES
    tr, te = sig[sig["date"] < test_from], sig[sig["date"] >= test_from]

    def train(d):
        mu, sd = d[X_cols].mean(), d[X_cols].std().replace(0, 1)
        m = LogisticRegression(C=0.3, max_iter=2000)
        m.fit((d[X_cols] - mu) / sd, d["win"])
        return m, mu, sd

    m, mu, sd = train(tr)
    p = m.predict_proba((te[X_cols] - mu) / sd)[:, 1]
    te = te.assign(p=p)
    metrics = {"n_train": int(len(tr)), "n_test": int(len(te)), "test_from": test_from,
               "auc": float(roc_auc_score(te["win"], p)) if te["win"].nunique() > 1 else None,
               "brier": float(brier_score_loss(te["win"], p)), "base_rate_test": float(te["win"].mean())}
    # Produktivmodell auf allen Daten
    m2, mu2, sd2 = train(sig)
    model = {"features": X_cols, "mean": mu2.round(6).tolist(), "std": sd2.round(6).tolist(),
             "coef": np.round(m2.coef_[0], 6).tolist(), "intercept": float(m2.intercept_[0]),
             "base_rate": float(sig["win"].mean()), "metrics_out_of_sample": metrics}
    return model, te


def bin_table(d: pd.DataFrame, by: str, bins=None, labels=None) -> pd.DataFrame:
    g = pd.cut(d[by], bins=bins, labels=labels, include_lowest=True) if bins is not None else d[by]
    t = d.groupby(g, observed=True).agg(n=("win", "size"), setups=("key", "nunique"), trefferquote=("win", "mean"),
                                        avg_R=("R", "mean"))
    t["trefferquote"] = (t["trefferquote"] * 100).round(1)
    t["avg_R"] = t["avg_R"].round(2)
    return t


def run(period: str, limit: int | None) -> None:
    os.makedirs(DATA, exist_ok=True)
    uni = load_universe()
    if limit:
        uni = uni.head(limit)
    bench_syms = sorted(set(INDEX_BENCHMARK.values()))
    prices = download(uni["ticker"].tolist() + bench_syms, period)
    rows = []
    t0 = time.time()
    for k, (_, u) in enumerate(uni.iterrows()):
        df = prices.get(u["ticker"])
        if df is None:
            continue
        try:
            rows += signals_for(u["ticker"], df, prices.get(benchmark_for(u["indices"])))
        except Exception as exc:  # noqa: BLE001
            print(f"[signale] {u['ticker']}: {exc}")
        if k % 50 == 49:
            print(f"[signale] {k + 1}/{len(uni)} · {len(rows)} Zeilen · {time.time() - t0:.0f}s")
    allsig = pd.DataFrame(rows)
    fill_rate = float(allsig["filled"].mean())
    sig = allsig[allsig["filled"] == 1].dropna(subset=chart.FEATURES).copy()
    sig.to_csv(os.path.join(DATA, "backtest_signals.csv.gz"), index=False, compression="gzip")

    last = pd.to_datetime(sig["date"]).max()
    test_from = (last - pd.Timedelta(days=365)).strftime("%Y-%m-%d")
    model, te = fit(sig, test_from)

    # Schwellen für den Top-10-Bericht aus den Testdaten (außerhalb der Trainingszeit):
    # Einstieg ab der Wahrscheinlichkeit, ab der der Durchschnittsertrag ≥ +0,25 R ist und ≥ 150 Fälle bleiben.
    te_tf = te[te["trend_aligned"] == 1]
    p_enter = 0.55
    for th in np.arange(0.30, 0.80, 0.01):
        sub = te_tf[te_tf["p"] >= th]
        if len(sub) >= 150 and sub["R"].mean() >= 0.25:
            p_enter = round(float(th), 2)
            break
    model["p_enter"] = p_enter
    model["p_exit"] = round(max(0.25, p_enter - 0.08), 2)
    model["fill_rate"] = fill_rate
    model["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    model["period"] = period
    model["n_signals"] = int(len(sig))
    model["n_setups"] = int(sig["key"].nunique())
    # Stützung (für die Confidence): Anzahl historischer Fälle je Wahrscheinlichkeitsklasse
    pall = 1 / (1 + np.exp(-(model["intercept"] + ((sig[chart.FEATURES] - model["mean"]) / model["std"]).values
                             @ np.array(model["coef"]))))
    sig["p"] = pall
    edges = [0, .2, .3, .4, .5, .6, .7, 1]
    sup = sig.groupby(pd.cut(sig["p"], edges, include_lowest=True), observed=False).agg(
        n=("win", "size"), hit=("win", "mean"), R=("R", "mean"))
    model["support"] = {"edges": edges, "n": sup["n"].astype(int).tolist(),
                        "hit": sup["hit"].fillna(0).round(4).tolist(), "avg_R": sup["R"].fillna(0).round(3).tolist()}
    with open(os.path.join(DATA, "prob_model.json"), "w", encoding="utf-8") as fh:
        json.dump(model, fh, ensure_ascii=False, indent=1)

    # ---------------------------------------------------------- Bericht
    m = model["metrics_out_of_sample"]
    rel = bin_table(te, "p", bins=[0, .2, .3, .4, .5, .6, .7, 1])
    lines = [
        f"# Backtest Fibonacci-Setups · {model['generated_utc']} UTC",
        "",
        f"Zeitraum {period}, {len(uni)} Titel, {model['n_signals']:,} Signaltage aus {model['n_setups']:,} Setups. "
        f"Limit-Ausführungsquote {fill_rate * 100:.0f} %. Gewinn = Ziel 1 vor Stop innerhalb von {MAX_BARS} Handelstagen.",
        "",
        f"**Basisquote:** {model['base_rate'] * 100:.1f} % aller ausgeführten Setups erreichen Ziel 1 vor dem Stop.",
        "",
        f"**Modellgüte außerhalb der Trainingszeit** (ab {m['test_from']}, {m['n_test']:,} Signale): "
        f"AUC {m['auc']:.3f} (0,5 = Zufall), Brier {m['brier']:.3f}.",
        f"**Schwellen:** Aufnahme in die Top 10 ab {p_enter:.0%}, Verbleib bis {model['p_exit']:.0%}.",
        "",
        "## Trefferquote nach übergeordnetem Trend (EMA 50/200)",
        "Long im Aufwärtstrend bzw. Short im Abwärtstrend = mit dem Trend.",
        "",
        bin_table(sig.assign(rt=np.where(sig["trend_aligned"] == 1, "mit Trend",
                                         np.where(sig["trend_against"] == 1, "gegen Trend", "seitwärts")) + " · "
                                + sig["setup"]), "rt").to_markdown(),
        "",
        "## Trefferquote nach EMA-Fächer (5>13>20>50>200, in Tradingrichtung, −1 … +1)",
        "",
        bin_table(sig, "stack", bins=[-1.01, -0.5, 0, 0.5, 1.01],
                  labels=["klar dagegen", "eher dagegen", "eher dafür", "klar dafür"]).to_markdown(),
        "",
        "## Umkehrkerze am Signaltag",
        "",
        bin_table(sig, "trigger").to_markdown(),
        "",
        "## Kalibrierung außerhalb der Trainingszeit (vorhergesagt vs. eingetreten)",
        "",
        rel.to_markdown(),
        "",
        "## Modellgewichte (standardisiert, + = erhöht die Wahrscheinlichkeit)",
        "",
        pd.Series(model["coef"], index=model["features"]).sort_values().round(3).to_frame("Gewicht").to_markdown(),
        "",
        "Hinweis: heutiges Index-Universum (Survivorship Bias), Gebühren und Spreads nicht berücksichtigt.",
    ]
    with open(os.path.join(DATA, "backtest_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines[:12]))


if __name__ == "__main__":
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else None
    run(sys.argv[1] if len(sys.argv) > 1 else "6y", lim)
