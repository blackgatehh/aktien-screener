"""Täglicher Aktien-Screener nach dem Framework „Aktien Analyse v2“.

Aufruf:
    python screener.py                # Kurse laden, Setups bewerten, Ergebnisse schreiben
    python screener.py --fundamentals # zusätzlich Fundamentaldaten neu laden (wöchentlich)

Ausgabe in data/:
    screener_latest.json   Kandidatenlisten, Marktumfeld, Metadaten
    screener_latest.csv    alle Titel mit allen Kennzahlen
    charts_latest.json     Kursverlauf + Zonen der Top-Kandidaten (für das Dashboard)
    fundamentals.csv       Fundamentaldaten (Cache, wöchentlich)
    signals_log.csv        alle A/B-Signale (für die spätere Auswertung der Trefferquote)
"""
from __future__ import annotations

import argparse
import re
import json
import math
import os
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import chart
import selection
from indicators import atr, candle, ema, lin, open_gaps, rsi
from universe import INDEX_BENCHMARK, benchmark_for, load_universe

DATA = os.path.join(os.path.dirname(__file__), "data")
FUND_FILE = os.path.join(DATA, "fundamentals.csv")
VERSION = "screener-v3 / framework v3.0"
MODEL_FILE = os.path.join(DATA, "prob_model.json")
STATE_FILE = os.path.join(DATA, "top10_state.json")
try:
    with open(MODEL_FILE, encoding="utf-8") as _fh:
        MODEL = json.load(_fh)
except FileNotFoundError:
    MODEL = None


# ----------------------------------------------------------------- Daten laden
def download(tickers: list[str], period: str = "2y") -> dict[str, pd.DataFrame]:
    import yfinance as yf

    out: dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), 150):
        chunk = tickers[i:i + 150]
        for attempt in range(3):
            try:
                raw = yf.download(chunk, period=period, interval="1d", group_by="ticker",
                                  auto_adjust=False, threads=True, progress=False)
                break
            except Exception as exc:  # noqa: BLE001
                print(f"[download] Fehler {exc}, neuer Versuch")
                time.sleep(10 * (attempt + 1))
        else:
            continue
        for t in chunk:
            try:
                df = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
                df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
                if len(df) >= 220:
                    out[t] = df
            except KeyError:
                pass
        time.sleep(2)
    print(f"[download] {len(out)}/{len(tickers)} Titel mit ausreichender Historie")
    return out


def load_fundamentals(tickers: list[str], refresh: bool) -> pd.DataFrame:
    if not refresh and os.path.exists(FUND_FILE):
        return pd.read_csv(FUND_FILE).set_index("ticker")
    import yfinance as yf

    rows = []
    keys = ["shortName", "sector", "industry", "currency", "marketCap", "forwardPE", "trailingPE",
            "enterpriseToEbitda", "freeCashflow", "trailingPegRatio", "priceToBook", "priceToSalesTrailing12Months",
            "returnOnEquity", "grossMargins", "totalDebt", "totalCash", "ebitda", "netIncomeToCommon",
            "earningsGrowth", "shortPercentOfFloat", "earningsTimestamp", "recommendationMean", "targetMeanPrice"]
    for i, t in enumerate(tickers):
        try:
            tk = yf.Ticker(t)
            info = tk.info
            try:
                isin = tk.isin
            except Exception:  # noqa: BLE001
                isin = None
            rows.append({"ticker": t, **{k: info.get(k) for k in keys},
                         "isin": isin if isin and isin != "-" else None})
        except Exception as exc:  # noqa: BLE001
            print(f"[fund] {t}: {exc}")
        if i % 50 == 49:
            print(f"[fund] {i + 1}/{len(tickers)}")
            time.sleep(3)
    df = pd.DataFrame(rows).set_index("ticker")
    df["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    df.to_csv(FUND_FILE)
    return df


# --------------------------------------------------------- Fundamental-Scores
def _num(x) -> float:
    try:
        x = float(x)
        return x if math.isfinite(x) else np.nan
    except (TypeError, ValueError):
        return np.nan


def _wavg(parts: list[tuple[float, float]]) -> float:
    parts = [(v, w) for v, w in parts if np.isfinite(v)]
    if not parts:
        return np.nan
    return sum(v * w for v, w in parts) / sum(w for _, w in parts)


def valuation_score(f: pd.Series) -> tuple[float, str]:
    sector, industry = str(f.get("sector", "")), str(f.get("industry", ""))
    mcap, fcf, ebitda = _num(f.get("marketCap")), _num(f.get("freeCashflow")), _num(f.get("ebitda"))
    fwd = _num(f.get("forwardPE"))
    fcf_yield = fcf / mcap * 100 if mcap and np.isfinite(fcf) and mcap > 0 else np.nan
    badge = ""
    is_fin = sector == "Financial Services" and any(k in industry for k in ("Bank", "Insurance"))
    unprofitable = (np.isfinite(ebitda) and ebitda <= 0) or not (np.isfinite(fwd) and fwd > 0)
    if unprofitable and not is_fin:
        ps = _num(f.get("priceToSalesTrailing12Months"))
        return min(lin(ps, 1, 15), 66) if np.isfinite(ps) else np.nan, "kein Gewinn · nur KUV"
    second = lin(_num(f.get("priceToBook")), 0.8, 3.0) if is_fin else lin(_num(f.get("enterpriseToEbitda")), 6, 30)
    s = _wavg([(lin(fwd, 10, 40), .30), (second, .25), (lin(fcf_yield, 8, 0), .25),
               (lin(_num(f.get("trailingPegRatio")), 0.5, 3.0), .20)])
    cyclical = sector in ("Energy", "Basic Materials") or any(
        k in industry for k in ("Semiconductor", "Auto", "Steel", "Chemical", "Oil"))
    if cyclical and np.isfinite(s):
        s, badge = min(s, 70), "Zykliker · Deckel 70"
    return s, badge


def quality_score(f: pd.Series) -> float:
    debt, cash, ebitda = _num(f.get("totalDebt")), _num(f.get("totalCash")), _num(f.get("ebitda"))
    nd_ebitda = (debt - cash) / ebitda if all(np.isfinite([debt, cash, ebitda])) and ebitda > 0 else np.nan
    fcf, ni = _num(f.get("freeCashflow")), _num(f.get("netIncomeToCommon"))
    conv = fcf / ni * 100 if np.isfinite(fcf) and np.isfinite(ni) and ni > 0 else np.nan
    roe = _num(f.get("returnOnEquity")) * 100
    return _wavg([(lin(roe, 20, 0), .35), (lin(nd_ebitda, 0, 4), .25), (lin(conv, 100, 0), .20)])


def label(score: float, hi: str, mid: str, lo: str) -> str:
    if not np.isfinite(score):
        return "–"
    return hi if score >= 66 else lo if score < 33 else mid


# ------------------------------------------------------------- Technik je Titel
def analyse(t: str, df: pd.DataFrame, bench: pd.DataFrame | None) -> dict:
    c = df["Close"]
    last = float(c.iloc[-1])
    a = float(atr(df).iloc[-1])
    sma200 = c.rolling(200).mean()
    s200, s200_prev = float(sma200.iloc[-1]), float(sma200.iloc[-21])
    e = {n: float(ema(c, n).iloc[-1]) for n in (5, 13, 20, 50)}
    r = rsi(c)
    rsi_now, rsi_5 = float(r.iloc[-1]), float(r.iloc[-6])
    hi52, lo52 = float(df["High"].tail(252).max()), float(df["Low"].tail(252).min())
    perf = c.iloc[-22] / c.iloc[-253] - 1 if len(c) > 253 else np.nan
    bperf = np.nan
    if bench is not None and len(bench) > 253:
        bc = bench["Close"]
        bperf = bc.iloc[-22] / bc.iloc[-253] - 1
    rel = (perf - bperf) * 100 if np.isfinite(perf) and np.isfinite(bperf) else np.nan
    vol_ratio = float(df["Volume"].iloc[-1] / df["Volume"].tail(51).head(50).mean()) if df["Volume"].tail(51).head(50).mean() > 0 else np.nan

    # Momentum-Score (Framework, ohne Revisionen: 40/40/20)
    up200 = s200 > s200_prev * 1.002
    flat_or_down = not up200
    if last > s200 and up200:
        trend_pts = 100
    elif last > s200:
        trend_pts = 60
    elif up200:
        trend_pts = 40
    else:
        trend_pts = 0
    mom = _wavg([(trend_pts, .40), (lin(rel, 30, -30), .40), (lin((last / hi52 - 1) * 100, 0, -50), .20)])

    row = {
        "ticker": t, "close": last, "atr": a, "atr_pct": a / last * 100, "sma200": s200,
        "sma200_rising": bool(up200), "ema5": e[5], "ema13": e[13], "ema20": e[20], "ema50": e[50],
        "rsi": rsi_now, "rsi_5ago": rsi_5, "hi52": hi52, "lo52": lo52,
        "dist_hi52_pct": (last / hi52 - 1) * 100, "perf_12m1m_pct": perf * 100 if np.isfinite(perf) else np.nan,
        "rel_bench_pp": rel, "vol_ratio": vol_ratio, "momentum": mom, "candle": candle(df, a),
        "date": df.index[-1].strftime("%Y-%m-%d"),
    }

    # Kurslücken
    gaps = open_gaps(df)
    below = [g for g in gaps if g["to"] < last]
    above = [g for g in gaps if g["from"] > last]
    gb = max(below, key=lambda g: g["to"]) if below else None
    ga = min(above, key=lambda g: g["from"]) if above else None
    row.update({
        "gap_below_from": gb["from"] if gb else np.nan, "gap_below_to": gb["to"] if gb else np.nan,
        "gap_below_dist_pct": (gb["to"] / last - 1) * 100 if gb else np.nan,
        "gap_above_from": ga["from"] if ga else np.nan, "gap_above_to": ga["to"] if ga else np.nan,
        "gap_above_dist_pct": (ga["from"] / last - 1) * 100 if ga else np.nan,
    })

    # Chartanalyse v3: EMA 5/13/20/50/200, Kreuzungen, Fibonacci-Setup, Wahrscheinlichkeit
    f = chart.chart_frame(df)
    t = len(f) - 1
    fr = f.iloc[t]
    bside = float(chart.bench_side_series(bench, f.index).iloc[-1])
    row.update({"ema200": float(fr["ema200"]), "stack": float(fr["stack"]), "slope200": float(fr["slope200"]),
                "x5_13": fr["x5_13"], "x20_50": fr["x20_50"], "x50_200": fr["x50_200"],
                "d200_atr": float(fr["d200_atr"]), "trend": chart.trend_class(fr), "ema_text": chart.ema_text(fr)})
    row.update({"setup": "", "zone_lo": np.nan, "zone_hi": np.nan, "stop": np.nan, "t1": np.nan,
                "t2": np.nan, "crv": np.nan, "status": "Beobachtung", "zone_dist_pct": np.nan,
                "p_win": np.nan, "p_avg3": np.nan, "days_valid": 0, "trend_ok": False, "setup_key": ""})
    st = chart.setup_at(f, t)
    if st is None:
        return row
    longs = st["setup"] == "long"
    H, L = st["swing_high"], st["swing_low"]
    # Ziel 1 = 1 R (so weit wie der Stop, Backtest: ca. 55 % Treffer), Ziel 2 = Swing-Extrem (ca. 22 %)
    risk_abs = abs(st["entry"] - st["stop"])
    t1_1r = st["entry"] + risk_abs if longs else st["entry"] - risk_abs
    row.update({"setup": st["setup"], "zone_lo": st["zone_lo"], "zone_hi": st["zone_hi"], "stop": st["stop"],
                "t1": t1_1r, "t2": st["t1"], "t3": st["t2"], "crv": st["crv_entry"],
                "zone_dist_pct": st["zone_dist_pct"],
                "fib382": (H - 0.382 * (H - L)) if longs else (L + 0.382 * (H - L)),
                "swing_high": H, "swing_low": L,
                "swing_high_date": f.index[st["hi_idx"]].strftime("%Y-%m-%d"),
                "swing_low_date": f.index[st["lo_idx"]].strftime("%Y-%m-%d"),
                "trend_ok": chart.trend_ok(st, fr), "retrace_pct": st["retrace"] * 100,
                "setup_key": f"{st['setup']}|{f.index[st['hi_idx']].date()}|{f.index[st['lo_idx']].date()}"})
    if st["broken"]:
        row["status"] = "Setup gebrochen"
    elif st["zone_dist_pct"] == 0:
        row["status"] = "In der Kaufzone" if longs else "In der Short-Zone"
    elif longs:
        row["status"] = (f"{st['zone_dist_pct']:.1f} % über Kaufzone" if st["zone_dist_pct"] > 0
                         else "unter Kaufzone, über Stop")
    else:
        row["status"] = (f"{-st['zone_dist_pct']:.1f} % unter Short-Zone" if st["zone_dist_pct"] < 0
                         else "über Short-Zone, unter Stop")
    # Wahrscheinlichkeit heute und Beständigkeit: dasselbe Setup (gleicher Swing) an den Vortagen
    if MODEL and not st["broken"]:
        bs = chart.bench_side_series(bench, f.index).values
        br = chart.bench_ret_series(bench, f.index).values
        hist = []
        for k in range(0, 10):
            tk = t - k
            sk = st if k == 0 else chart.setup_at(f, tk)
            if (sk is None or sk["broken"] or sk["setup"] != st["setup"] or sk["hi_idx"] != st["hi_idx"]
                    or sk["lo_idx"] != st["lo_idx"] or abs(sk["zone_dist_pct"]) > 5
                    or not chart.trend_ok(sk, f.iloc[tk])):
                break
            hist.append(chart.predict(MODEL, chart.features(f, tk, sk, bs[tk], br[tk])))
        row["p_win"] = hist[0] if hist else chart.predict(MODEL, chart.features(f, t, st, bs[t], br[t]))
        row["days_valid"] = len(hist)
        row["p_avg3"] = float(np.mean(hist[:3])) if hist else row["p_win"]
        row["p_std"] = float(np.std(hist[:5])) if len(hist) > 1 else np.nan
        cnd = chart.candle_at(f, t)
        row["candle"] = cnd
    return row


# ------------------------------------------------------------ Setup-Bewertung
def setup_score(r: pd.Series, regime: str) -> float:
    if r["setup"] not in ("long", "short") or r["status"] == "Setup gebrochen":
        return 0.0
    longs = r["setup"] == "long"
    last, zlo, zhi = r["close"], r["zone_lo"], r["zone_hi"]
    pts = 0.0
    # 1) Trend (25): EMA 50/200-Trend in Tradingrichtung, dazu der EMA-Fächer 5/13/20/50/200
    s = 1 if longs else -1
    tc = r.get("trend", "seitwärts")
    aligned = (tc == "auf" and longs) or (tc == "ab" and not longs)
    against = (tc == "ab" and longs) or (tc == "auf" and not longs)
    pts += (17 if aligned else 0 if against else 5) + max(0.0, s * r.get("stack", 0) / 4) * 8
    # 2) Lage zur Zone (25)
    d = r["zone_dist_pct"]
    if d == 0:
        pts += 25
    elif np.isfinite(d):
        near = (0 < d <= 3) if longs else (-3 <= d < 0)
        pts += 12 if near else 6 if abs(d) <= 6 else 0
    # 3) Konfluenz (15): offene Lücke, EMA50 oder SMA200 in/an der Zone
    lo_b, hi_b = zlo * 0.985, zhi * 1.015
    conf = 0
    for lvl in (r["ema50"], r["sma200"]):
        if lo_b <= lvl <= hi_b:
            conf += 6
    gap_lo, gap_hi = (r["gap_below_from"], r["gap_below_to"]) if longs else (r["gap_above_from"], r["gap_above_to"])
    if np.isfinite(gap_lo) and gap_hi >= lo_b and gap_lo <= hi_b:
        conf += 8
    pts += min(conf, 15)
    # 4) Auslöser (15): Umkehrkerze bzw. drehender RSI
    bull = r["candle"] in ("hammer", "bull_engulfing")
    bear = r["candle"] in ("shooting_star", "bear_engulfing")
    if (longs and bull) or (not longs and bear):
        pts += 15
    elif longs and r["rsi_5ago"] < 40 and r["rsi"] > r["rsi_5ago"]:
        pts += 8
    elif not longs and r["rsi_5ago"] > 60 and r["rsi"] < r["rsi_5ago"]:
        pts += 8
    # 5) CRV (10)
    crv = r["crv"]
    pts += 10 if crv >= 3 else 6 if crv >= 2 else 0
    # 6) Fundamentaldaten (10) – für Shorts umgekehrt
    fund = _wavg([(r.get("valuation", np.nan), .5), (r.get("quality", np.nan), .5)])
    if np.isfinite(fund):
        f = fund if longs else 100 - fund
        pts += 10 if f >= 60 else 5 if f >= 45 else 0
    # Marktumfeld
    if longs and regime == "Risk-off":
        pts *= 0.8
    if not longs and regime == "Risk-on":
        pts *= 0.9
    return round(pts, 1)


def grade(r: pd.Series) -> str:
    s, crv = r["score"], r["crv"]
    trig = (r["setup"] == "long" and r["candle"] in ("hammer", "bull_engulfing")) or \
           (r["setup"] == "short" and r["candle"] in ("shooting_star", "bear_engulfing"))
    in_zone = r["zone_dist_pct"] == 0
    if s >= 75 and trig and in_zone and crv >= 3:
        return "A"
    if s >= 60 and crv >= 2:
        return "B"
    if s >= 45:
        return "C"
    return "D"


def market_regime(benchmarks: dict[str, pd.DataFrame], vix: pd.DataFrame | None) -> dict:
    out = {}
    v = float(vix["Close"].iloc[-1]) if vix is not None and len(vix) else np.nan
    for name, sym in (("USA", "^GSPC"), ("Deutschland", "^GDAXI"), ("Europa", "^STOXX50E")):
        b = benchmarks.get(sym)
        if b is None or len(b) < 220:
            continue
        c = b["Close"]
        s200 = c.rolling(200).mean()
        above_rising = c.iloc[-1] > s200.iloc[-1] and s200.iloc[-1] > s200.iloc[-21]
        calm = np.isfinite(v) and v < 20
        stress = np.isfinite(v) and v > 25
        regime = "Risk-on" if above_rising and calm else ("Risk-off" if (c.iloc[-1] < s200.iloc[-1] and stress) else "Neutral")
        out[name] = {"regime": regime, "index": round(float(c.iloc[-1]), 2), "sma200": round(float(s200.iloc[-1]), 2)}
    out["VIX"] = round(v, 2) if np.isfinite(v) else None
    return out


def region_of(indices: str) -> str:
    if "DAX" in indices or "MDAX" in indices:
        return "Deutschland"
    if "EUROSTOXX50" in indices:
        return "Europa"
    return "USA"


# ------------------------------------------------------------------ Hauptlauf
def run(refresh_fund: bool) -> None:
    os.makedirs(DATA, exist_ok=True)
    uni = load_universe()
    tickers = uni["ticker"].tolist()
    bench_syms = list(INDEX_BENCHMARK.values()) + ["^VIX"]
    prices = download(tickers + bench_syms)
    benchmarks = {s: prices.get(s) for s in bench_syms}
    regime = market_regime(benchmarks, benchmarks.get("^VIX"))

    fund = load_fundamentals(tickers, refresh_fund or not os.path.exists(FUND_FILE))

    rows = []
    for _, u in uni.iterrows():
        t = u["ticker"]
        df = prices.get(t)
        if df is None:
            continue
        try:
            r = analyse(t, df, benchmarks.get(benchmark_for(u["indices"])))
        except Exception as exc:  # noqa: BLE001
            print(f"[analyse] {t}: {exc}")
            continue
        r["indices"] = u["indices"]
        r["region"] = region_of(u["indices"])
        if t in fund.index:
            f = fund.loc[t]
            nm = str(f.get("shortName") or t)
            r["name"] = re.sub(r"\s{2,}\S{0,2}$", "", nm).strip()  # yfinance hängt bei Xetra-Titeln Füllzeichen an
            r["sector"] = f.get("sector")
            r["currency"] = f.get("currency")
            r["valuation"], r["val_badge"] = valuation_score(f)
            r["quality"] = quality_score(f)
            r["fwd_pe"] = _num(f.get("forwardPE"))
            r["ev_ebitda"] = _num(f.get("enterpriseToEbitda"))
            r["earnings_ts"] = _num(f.get("earningsTimestamp"))
            r["target_mean"] = _num(f.get("targetMeanPrice"))
            isin = f.get("isin") if "isin" in f.index else None
            r["isin"] = isin if isinstance(isin, str) and len(isin) == 12 else None
            r["wkn"] = isin[5:11] if r["isin"] and isin.startswith("DE") else None
        rows.append(r)

    res = pd.DataFrame(rows)
    res["val_label"] = res["valuation"].apply(lambda s: label(s, "günstig", "fair", "teuer"))
    res["mom_label"] = res["momentum"].apply(lambda s: label(s, "stark", "neutral", "schwach"))
    res["qual_label"] = res["quality"].apply(lambda s: label(s, "hoch", "mittel", "schwach"))
    res["score"] = res.apply(lambda r: setup_score(r, regime.get(r["region"], {}).get("regime", "Neutral")), axis=1)
    res["grade"] = res.apply(grade, axis=1)
    now = datetime.now(timezone.utc)
    res["earnings_days"] = res["earnings_ts"].apply(
        lambda ts: (datetime.fromtimestamp(ts, timezone.utc) - now).days if np.isfinite(ts) else np.nan)
    res["earnings_soon"] = res["earnings_days"].between(0, 14)

    # Handelbarkeit: Einstieg (Kurs in der Zone, sonst Zonenmitte), Abstände, Zeit bis T1, Knock-out-Hebel
    def tradeable(r):
        if r["setup"] not in ("long", "short") or not np.isfinite(r["zone_lo"]):
            return pd.Series({"entry": np.nan, "pot_t1_pct": np.nan, "risk_pct": np.nan, "crv_entry": np.nan,
                              "weeks_t1": np.nan, "ko_level": np.nan, "ko_leverage": np.nan})
        longs = r["setup"] == "long"
        inzone = r["zone_lo"] <= r["close"] <= r["zone_hi"]
        entry = r["close"] if inzone else (r["zone_lo"] + r["zone_hi"]) / 2
        a = r["atr_pct"] / 100 * r["close"]
        pot = (r["t1"] / entry - 1) * 100 if longs else (1 - r["t1"] / entry) * 100
        risk = abs(r["stop"] / entry - 1) * 100
        ko = r["stop"] - 2 * a if longs else r["stop"] + 2 * a
        n_atr = abs(r["t1"] - entry) / a if a > 0 else np.nan
        return pd.Series({"entry": entry, "pot_t1_pct": pot, "risk_pct": risk,
                          "crv_entry": pot / risk if risk > 0 else np.nan,
                          "weeks_t1": (n_atr ** 2) / 5 if np.isfinite(n_atr) else np.nan,  # Random-Walk-Näherung
                          "ko_level": ko, "ko_leverage": entry / abs(entry - ko) if entry != ko else np.nan})

    res = pd.concat([res, res.apply(tradeable, axis=1)], axis=1)
    # Vorauswahl für den Top-10-Bericht: Note A/B, nah an der Zone, CRV ab Einstieg ≥ 2, Stop ≤ 10 % entfernt
    res["report_candidate"] = (res["grade"].isin(["A", "B"]) & (res["crv_entry"] >= 2) & (res["risk_pct"] <= 10)
                               & (res["zone_dist_pct"].abs() <= 5) & (res["status"] != "Setup gebrochen"))

    # Top 10 mit Gedächtnis (Framework v3)
    asof = str(res["date"].max())
    top10 = selection.select(res, MODEL, STATE_FILE, asof)
    top10["generated_utc"] = now.strftime("%Y-%m-%d %H:%M")
    top10["market"] = regime
    with open(os.path.join(DATA, "top10.json"), "w", encoding="utf-8") as fh:
        json.dump(top10, fh, ensure_ascii=False, indent=1, default=str)
    print(f"[top10] {len(top10['picks'])} Titel · raus: {len(top10['removed'])} · Schwellen {top10.get('thresholds')}")

    # Kandidatenlisten
    longs = res[(res["setup"] == "long") & res["grade"].isin(["A", "B", "C"])].sort_values("score", ascending=False)
    shorts = res[(res["setup"] == "short") & res["grade"].isin(["A", "B", "C"])].sort_values("score", ascending=False)
    breakouts = res[(res["close"] >= res["hi52"] * 0.99) & (res["vol_ratio"] >= 1.5) & res["sma200_rising"]] \
        .sort_values("vol_ratio", ascending=False)
    gapfill = res[(res["gap_below_dist_pct"] > -6) & (res["close"] > res["sma200"]) & res["sma200_rising"]] \
        .sort_values("gap_below_dist_pct", ascending=False)

    cols = ["ticker", "name", "isin", "wkn", "currency", "region", "indices", "sector", "date", "close", "grade", "score", "setup", "status",
            "zone_lo", "zone_hi", "stop", "t1", "t2", "t3", "crv", "candle", "rsi", "atr_pct", "sma200", "sma200_rising",
            "ema20", "ema50", "dist_hi52_pct", "rel_bench_pp", "vol_ratio", "momentum", "mom_label", "valuation",
            "val_label", "val_badge", "quality", "qual_label", "fwd_pe", "ev_ebitda", "gap_below_from",
            "gap_below_to", "gap_below_dist_pct", "gap_above_from", "gap_above_to", "gap_above_dist_pct",
            "swing_high", "swing_high_date", "swing_low", "swing_low_date", "earnings_days", "earnings_soon",
            "target_mean", "entry", "pot_t1_pct", "risk_pct", "crv_entry", "weeks_t1", "ko_level", "ko_leverage",
            "report_candidate", "ema200", "stack", "trend", "trend_ok", "ema_text", "x5_13", "x20_50", "x50_200",
            "p_win", "p_avg3", "days_valid", "setup_key", "retrace_pct"]
    cols = [c for c in cols if c in res.columns]

    def records(df: pd.DataFrame, n: int) -> list[dict]:
        return json.loads(df[cols].head(n).to_json(orient="records", double_precision=4))

    payload = {
        "generated_utc": now.strftime("%Y-%m-%d %H:%M"),
        "version": VERSION,
        "universe_size": len(uni),
        "analysed": len(res),
        "fundamentals_updated": str(fund["updated"].iloc[0]) if "updated" in fund.columns and len(fund) else None,
        "market": regime,
        "top_long": records(longs, 25),
        "top_short": records(shorts, 15),
        "breakouts": records(breakouts, 10),
        "gap_fill_watch": records(gapfill, 15),
        "report_pool": records(res[res["report_candidate"]].sort_values("score", ascending=False), 40),
        "grade_counts": res["grade"].value_counts().to_dict(),
    }
    with open(os.path.join(DATA, "screener_latest.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    res[cols].sort_values("score", ascending=False).to_csv(os.path.join(DATA, "screener_latest.csv"), index=False)

    # Chartdaten für die Top-Kandidaten
    charts = {}
    chart_tickers = list(dict.fromkeys([p["ticker"] for p in top10["picks"]] +
                                       pd.concat([longs.head(12), shorts.head(8), breakouts.head(5)])["ticker"].tolist()))
    for t in chart_tickers:
        df = prices[t].tail(180)
        c = prices[t]["Close"]
        charts[t] = {
            "d": [x.strftime("%Y-%m-%d") for x in df.index],
            "o": df["Open"].round(3).tolist(), "h": df["High"].round(3).tolist(),
            "l": df["Low"].round(3).tolist(), "c": df["Close"].round(3).tolist(),
            "ema5": ema(c, 5).tail(180).round(3).tolist(), "ema13": ema(c, 13).tail(180).round(3).tolist(),
            "ema20": ema(c, 20).tail(180).round(3).tolist(), "ema50": ema(c, 50).tail(180).round(3).tolist(),
            "ema200": ema(c, 200).tail(180).round(3).tolist(),
            "sma200": c.rolling(200).mean().tail(180).round(3).tolist(),
        }
    with open(os.path.join(DATA, "charts_latest.json"), "w", encoding="utf-8") as fh:
        json.dump(charts, fh)

    # Signal-Log für die Validierung (nur A/B, je Titel und Tag einmal)
    log_file = os.path.join(DATA, "signals_log.csv")
    sig = res[res["grade"].isin(["A", "B"])][["date", "ticker", "setup", "grade", "score", "close", "zone_lo",
                                               "zone_hi", "stop", "t1", "t2", "crv"]].copy()
    sig["logged_utc"] = now.strftime("%Y-%m-%d %H:%M")
    if os.path.exists(log_file):
        old = pd.read_csv(log_file)
        sig = pd.concat([old, sig]).drop_duplicates(subset=["date", "ticker", "setup"], keep="first")
    sig.to_csv(log_file, index=False)

    print(f"[fertig] {len(res)} Titel · Long A/B/C: {len(longs)} · Short A/B/C: {len(shorts)} · "
          f"Ausbrüche: {len(breakouts)} · Markt: {regime}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fundamentals", action="store_true", help="Fundamentaldaten neu laden")
    run(ap.parse_args().fundamentals)
