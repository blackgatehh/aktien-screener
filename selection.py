"""Top-10-Auswahl mit Gedächtnis (Framework v3).

Ziel: Beständige Plays statt täglich neuer Namen.
- Wahrscheinlichkeit: Modell aus dem Backtest (T1 vor Stop), geglättet über die letzten 3 Tage desselben Setups.
- Aufnahme: Trendfilter erfüllt, Setup seit mindestens 2 Handelstagen gültig, geglättete Wahrscheinlichkeit
  ≥ p_enter, kein Zahlentermin in den nächsten 5 Tagen.
- Verbleib: Ein Titel bleibt im Bericht, solange das Setup gilt und die Wahrscheinlichkeit ≥ p_exit ist
  (Hysterese). Er fliegt nur mit Grund raus (Stop, Ziel 1, Trend gekippt, Wahrscheinlichkeit gefallen …).
- Lieber weniger als zehn: Es werden nur Titel gezeigt, die die Schwellen erfüllen.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pandas as pd

MAX_PICKS, MAX_PER_SECTOR, MIN_DAYS = 10, 3, 2


def _f(x, default=np.nan) -> float:
    try:
        x = float(x)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def support_n(model: dict, p: float) -> int:
    sup = model.get("support") or {}
    edges, ns = sup.get("edges", []), sup.get("n", [])
    for i in range(len(ns)):
        if edges[i] <= p <= edges[i + 1]:
            return int(ns[i])
    return 0


def hist_hit(model: dict, p: float) -> float:
    sup = model.get("support") or {}
    edges, hit = sup.get("edges", []), sup.get("hit", [])
    for i in range(len(hit)):
        if edges[i] <= p <= edges[i + 1]:
            return float(hit[i])
    return np.nan


def confidence(r: pd.Series, model: dict) -> tuple[int, dict]:
    """Wie belastbar ist die Wahrscheinlichkeit? 0–100, vor News-Prüfung.

    Stützung (35): Zahl vergleichbarer Fälle im Backtest
    Beständigkeit (35): Tage, die das Setup schon gültig ist, und wie ruhig die Wahrscheinlichkeit ist
    Klarheit (30): EMA-Fächer in Tradingrichtung, kein Zahlentermin, Auslöser (Umkehrkerze / 5-13-Kreuzung)
    """
    p = _f(r.get("p_avg3"))
    n = support_n(model, p) if np.isfinite(p) else 0
    sup = min(35.0, 35 * math.log10(max(n, 1)) / math.log10(3000))
    d = int(_f(r.get("days_valid"), 0))
    stab = {0: 0, 1: 10, 2: 20, 3: 26, 4: 30}.get(d, 35)
    if _f(r.get("p_std"), 0) > 0.06:
        stab -= 10
    s = 1 if r["setup"] == "long" else -1
    stack = _f(r.get("stack"), 0) * s / 4
    clar = 15 if stack >= 0.99 else 10 if stack >= 0.5 else 4 if stack > 0 else 0
    ed = _f(r.get("earnings_days"))
    clar += 10 if not (np.isfinite(ed) and 0 <= ed <= 10) else 0
    trig = r.get("candle") in (("hammer", "bull_engulfing") if s > 0 else ("shooting_star", "bear_engulfing"))
    x513 = _f(r.get("x5_13"))
    clar += 5 if trig or (np.isfinite(x513) and np.sign(x513) == s and abs(x513) <= 3) else 0
    total = int(round(max(0, sup) + max(0, stab) + clar))
    return total, {"stuetzung": round(sup), "bestaendigkeit": max(0, stab), "klarheit": clar, "faelle": n}


def eligible(r: pd.Series) -> bool:
    if r.get("setup") not in ("long", "short") or r.get("status") == "Setup gebrochen" or not r.get("trend_ok"):
        return False
    d = _f(r.get("zone_dist_pct"))
    if not np.isfinite(d) or abs(d) > 5 or (r["setup"] == "long" and d < 0) or (r["setup"] == "short" and d > 0):
        return False
    return (_f(r.get("crv"), 0) >= 1.5 and _f(r.get("risk_pct"), 99) <= 10
            and np.isfinite(_f(r.get("p_avg3"))))


def exit_reason(r: pd.Series | None, key: str, p_exit: float) -> str:
    if r is None:
        return "keine Kursdaten"
    if r.get("setup_key") != key.split("::", 1)[1]:
        return "Setup beendet (Ziel 1 oder Stop erreicht, oder neues Swing-Muster)"
    if r.get("status") == "Setup gebrochen":
        return "Stop oder Ziel 1 erreicht"
    if not r.get("trend_ok"):
        return f"EMA-Trend gekippt ({r.get('trend')})"
    d = _f(r.get("zone_dist_pct"))
    if np.isfinite(d) and ((r["setup"] == "long" and d < 0) or (r["setup"] == "short" and d > 0)):
        return "Kurs durch die Zone Richtung Stop gelaufen"
    if np.isfinite(d) and abs(d) > 5:
        return "Kurs mehr als 5 % von der Zone weg (Einstieg verpasst)"
    if _f(r.get("p_avg3"), 0) < p_exit:
        return f"Wahrscheinlichkeit unter {p_exit:.0%} gefallen"
    return "Kriterien nicht mehr erfüllt"


def select(res: pd.DataFrame, model: dict | None, state_file: str, asof: str) -> dict:
    """Top-10 bestimmen und Zustand fortschreiben. asof = Datum der letzten Kerze (YYYY-MM-DD)."""
    state = {"asof": None, "top": {}, "prev_top": {}}
    if os.path.exists(state_file):
        with open(state_file, encoding="utf-8") as fh:
            state = json.load(fh)
    # Gleiches Datum nochmal gerechnet (z. B. manueller Lauf): vom Stand davor ausgehen
    prev = state.get("prev_top", {}) if state.get("asof") == asof else state.get("top", {})
    if not model:
        return {"picks": [], "removed": [], "note": "kein Wahrscheinlichkeitsmodell (backtest.py ausführen)"}
    p_in, p_out = float(model.get("p_enter", 0.55)), float(model.get("p_exit", 0.47))

    res = res.copy()
    res["key"] = res["ticker"] + "::" + res["setup_key"].fillna("")
    res["eligible"] = res.apply(eligible, axis=1)
    tr = float(model.get("target_R", 1.0))
    res["ev_R"] = res["p_avg3"] * tr - (1 - res["p_avg3"])
    by_key = {k: r for k, r in res.set_index("key", drop=False).iterrows()}
    by_ticker = {r["ticker"]: r for _, r in res.iterrows()}

    keep, removed = [], []
    for key, info in prev.items():
        r = by_key.get(key)
        ok = r is not None and r["eligible"] and _f(r["p_avg3"], 0) >= p_out
        if ok:
            keep.append(key)
        else:
            rr = r if r is not None else by_ticker.get(key.split("::")[0])
            removed.append({"ticker": key.split("::")[0], "name": (rr.get("name") if rr is not None else None),
                            "setup": key.split("::")[1].split("|")[0], "since": info.get("since"),
                            "reason": exit_reason(rr, key, p_out)})

    new = res[res["eligible"] & ~res["key"].isin(keep) & (res["p_avg3"] >= p_in) & (res["days_valid"] >= MIN_DAYS)
              & ~res["earnings_days"].between(0, 5)].sort_values("ev_R", ascending=False)
    chosen, sectors = [], {}
    for key in sorted(keep, key=lambda k: -_f(by_key[k]["ev_R"], -9)):
        chosen.append(key)
        sec = by_key[key].get("sector")
        sectors[sec] = sectors.get(sec, 0) + 1
    for _, r in new.iterrows():
        if len(chosen) >= MAX_PICKS:
            break
        if sectors.get(r.get("sector"), 0) >= MAX_PER_SECTOR:
            continue
        chosen.append(r["key"])
        sectors[r.get("sector")] = sectors.get(r.get("sector"), 0) + 1
    chosen = chosen[:MAX_PICKS]

    top, picks = {}, []
    for key in chosen:
        r = by_key[key]
        since = prev.get(key, {}).get("since", asof)
        top[key] = {"since": since}
        conf, parts = confidence(r, model)
        inzone = r["zone_dist_pct"] == 0
        pick = {k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in r.items()
                if k in ("ticker", "name", "isin", "wkn", "currency", "sector", "setup", "close", "zone_lo",
                         "zone_hi", "stop", "t1", "t2", "entry", "crv", "crv_entry", "risk_pct", "pot_t1_pct", "weeks_t1",
                         "ko_level", "ko_leverage", "trend", "ema_text", "stack", "ema20", "ema50", "ema200",
                         "rsi", "atr_pct", "earnings_days", "status", "candle", "swing_high", "swing_low",
                         "swing_high_date", "swing_low_date", "gap_below_from", "gap_below_to", "gap_above_from",
                         "gap_above_to", "days_valid", "p_win")}
        pick.update({
            "probability": round(float(r["p_avg3"]) * 100),
            "probability_today": round(float(r["p_win"]) * 100) if np.isfinite(_f(r["p_win"])) else None,
            "hist_hit": round(hist_hit(model, float(r["p_avg3"])) * 100),
            "hit_t2_hist": round(float(model.get("hit_swing_target", np.nan)) * 100),
            "ev_R": round(float(r["ev_R"]), 2),
            "confidence_base": conf, "confidence_parts": parts,
            "category": "Einstieg jetzt" if inzone else "Limit setzen",
            "status_report": "neu" if key not in prev else "bleibt",
            "in_report_since": since,
        })
        picks.append(pick)
    picks.sort(key=lambda p: (-p["probability"], -p["confidence_base"], -p["ev_R"]))
    for i, p in enumerate(picks, 1):
        p["rank"] = i

    with open(state_file, "w", encoding="utf-8") as fh:
        json.dump({"asof": asof, "top": top, "prev_top": prev,
                   "thresholds": {"p_enter": p_in, "p_exit": p_out}}, fh, ensure_ascii=False, indent=1)
    watch = res[res["eligible"] & ~res["key"].isin(chosen) & (res["p_avg3"] >= p_in - 0.05)] \
        .sort_values("ev_R", ascending=False).head(10)
    return {"asof": asof, "thresholds": {"p_enter": p_in, "p_exit": p_out}, "picks": picks, "removed": removed,
            "watch_next": [{"ticker": r["ticker"], "name": r.get("name"), "setup": r["setup"],
                            "probability": round(float(r["p_avg3"]) * 100), "days_valid": int(r["days_valid"])}
                           for _, r in watch.iterrows()],
            "base_rate": round(float(model.get("base_rate", np.nan)) * 100, 1),
            "model_metrics": model.get("metrics_out_of_sample")}
