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

MAX_PICKS, MAX_PER_SECTOR, MIN_DAYS = 10, 3, 1


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


ACT_MAX = 1.5      # Phase 3 Timing: Kurs in der Zone oder höchstens 1,5 % davor = handelbar
ALARM_MAX = 5.0    # bis 5 % vor der Zone: Alarm setzen
P_MIN = 0.50       # Long: Chart-Grundwahrscheinlichkeit mindestens Durchschnitt (Ziel 1 vor Stop)
P_MIN_SHORT = 0.43 # Short: Chart allein hat im Backtest keinen Vorteil → Aufnahme nur mit ≥ 2 News-Faktoren im Bericht
MAX_SHORTS = 4
KEEP = ("ticker", "name", "isin", "wkn", "currency", "sector", "setup", "close", "zone_lo", "zone_hi", "stop", "t1",
        "t2", "entry", "crv", "crv_entry", "risk_pct", "pot_t1_pct", "weeks_t1", "ko_level", "ko_leverage", "trend",
        "ema_text", "stack", "ema20", "ema50", "ema200", "rsi", "atr_pct", "earnings_days", "status", "candle",
        "swing_high", "swing_low", "swing_high_date", "swing_low_date", "gap_below_from", "gap_below_to",
        "gap_above_from", "gap_above_to", "days_valid", "p_win", "zone_dist_pct")


def chart_reasons(r: pd.Series) -> list[str]:
    """Phase 2 (Chart-Teil): konkrete, prüfbare Chartgründe in Tradingrichtung."""
    s = 1 if r["setup"] == "long" else -1
    out = []
    zl, zh = _f(r.get("zone_lo")) * 0.985, _f(r.get("zone_hi")) * 1.015
    for n in (20, 50, 200):
        e = _f(r.get(f"ema{n}"))
        if np.isfinite(e) and zl <= e <= zh:
            out.append(f"Zone trifft EMA {n} ({e:.2f})")
    c, e20 = _f(r.get("close")), _f(r.get("ema20"))
    if np.isfinite(e20) and (c - e20) * s < 0 and r.get("zone_dist_pct") == 0:
        out.append("Rücksetzer " + ("unter" if s > 0 else "über") + " die EMA 20 bis in die Zone")
    if r.get("candle") in ((("hammer", "bull_engulfing")) if s > 0 else ("shooting_star", "bear_engulfing")):
        out.append("Umkehrkerze heute (" + str(r.get("candle")).replace("_", " ") + ")")
    x = _f(r.get("x5_13"))
    if np.isfinite(x) and np.sign(x) == s and abs(x) <= 3:
        out.append("EMA 5 kreuzt EMA 13 in Tradingrichtung")
    if _f(r.get("stack"), 0) * s >= 3:
        out.append("EMA-Fächer klar in Tradingrichtung")
    gap_key = ("gap_below_from", "gap_below_to") if s > 0 else ("gap_above_from", "gap_above_to")
    g1, g2 = _f(r.get(gap_key[0])), _f(r.get(gap_key[1]))
    if np.isfinite(g1) and np.isfinite(g2) and min(g1, g2) * 0.98 <= (zl + zh) / 2 <= max(g1, g2) * 1.02:
        out.append("offenes Gap in der Zone")
    return out


def _pack(r: pd.Series, model: dict) -> dict:
    conf, parts = confidence(r, model)
    d = {k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in r.items() if k in KEEP}
    d.update({"probability": round(float(r["p_avg3"]) * 100),
              "probability_today": round(float(r["p_win"]) * 100) if np.isfinite(_f(r["p_win"])) else None,
              "confidence_base": conf, "confidence_parts": parts,
              "chart_reasons": chart_reasons(r), "ev_R": round(float(r["ev_R"]), 2)})
    return d


def select(res: pd.DataFrame, model: dict | None, state_file: str, asof: str) -> dict:
    """Phasen-Modell (v3.2): 1 Potenzial → 2 Validierung (Chart hier, News im Bericht) → 3 Timing.

    picks  = handelbare Setups (Kurs in der Zone oder ≤ 1,5 % davor), Long und Short, mit Chartgründen
    alarm  = saubere Setups 1,5–5 % vor der Zone (Kursalarm setzen, noch nicht handeln)
    Gedächtnis: Ein Titel bleibt in picks, solange er handelbar bleibt und das Setup gilt.
    """
    state = {"asof": None, "top": {}, "prev_top": {}}
    if os.path.exists(state_file):
        with open(state_file, encoding="utf-8") as fh:
            state = json.load(fh)
    prev = state.get("prev_top", {}) if state.get("asof") == asof else state.get("top", {})
    if not model:
        return {"picks": [], "removed": [], "alarm": [], "note": "kein Wahrscheinlichkeitsmodell"}
    tr = float(model.get("target_R", 1.0))

    res = res.copy()
    res["key"] = res["ticker"] + "::" + res["setup_key"].fillna("")
    res["eligible"] = res.apply(eligible, axis=1)
    res["ad"] = res["zone_dist_pct"].abs()
    res["ev_R"] = res["p_avg3"] * tr - (1 - res["p_avg3"])
    res["n_reasons"] = res.apply(lambda r: len(chart_reasons(r)) if r["eligible"] else 0, axis=1)
    by_key = {k: r for k, r in res.set_index("key", drop=False).iterrows()}
    by_ticker = {r["ticker"]: r for _, r in res.iterrows()}
    pmin = np.where(res["setup"] == "short", P_MIN_SHORT, P_MIN)
    act = res["eligible"] & (res["ad"] <= ACT_MAX) & (res["p_avg3"] >= pmin) & ~res["earnings_days"].between(0, 3)

    removed, chosen = [], []
    for key, info in prev.items():
        r = by_key.get(key)
        if r is not None and bool(act.get(r.name, False)):
            chosen.append(key)
            continue
        rr = r if r is not None else by_ticker.get(key.split("::")[0])
        reason = exit_reason(rr, key, P_MIN)
        if r is not None and r["eligible"] and r["ad"] > ACT_MAX:
            reason = "Kurs aus der Zone gelaufen" + (" (Richtung Ziel)" if r["ad"] > 0 else "") + " → Alarm-Liste"
        removed.append({"ticker": key.split("::")[0], "name": rr.get("name") if rr is not None else None,
                        "setup": key.split("::")[1].split("|")[0], "since": info.get("since"), "reason": reason})
    # Neue: Rangfolge nach Anzahl Chartgründe, dann Wahrscheinlichkeit
    cand = res[act & ~res["key"].isin(chosen)].sort_values(["n_reasons", "p_avg3"], ascending=False)
    # Platz für Shorts reservieren (bis MAX_SHORTS), Rest Longs
    shorts = cand[cand["setup"] == "short"].head(MAX_SHORTS)
    cand = pd.concat([shorts, cand[cand["setup"] == "long"]]).sort_values(["n_reasons", "p_avg3"], ascending=False)
    cand = pd.concat([shorts, cand[~cand["key"].isin(shorts["key"])]]) if len(shorts) else cand
    sectors = {}
    for k in chosen:
        sectors[by_key[k].get("sector")] = sectors.get(by_key[k].get("sector"), 0) + 1
    for _, r in cand.iterrows():
        if len(chosen) >= MAX_PICKS:
            break
        if sectors.get(r.get("sector"), 0) >= MAX_PER_SECTOR:
            continue
        chosen.append(r["key"])
        sectors[r.get("sector")] = sectors.get(r.get("sector"), 0) + 1

    top, picks = {}, []
    for key in chosen:
        r = by_key[key]
        since = prev.get(key, {}).get("since", asof)
        top[key] = {"since": since}
        p = _pack(r, model)
        p.update({"category": ("Einstieg jetzt" if r["zone_dist_pct"] == 0 else "Zone fast erreicht"),
                  "needs_news": r["setup"] == "short" or r["p_avg3"] < 0.52,
                  "status_report": "neu" if key not in prev else "bleibt", "in_report_since": since})
        picks.append(p)
    picks.sort(key=lambda p: (-len(p["chart_reasons"]), -p["probability"], -p["confidence_base"]))
    for i, p in enumerate(picks, 1):
        p["rank"] = i
    with open(state_file, "w", encoding="utf-8") as fh:
        json.dump({"asof": asof, "top": top, "prev_top": prev}, fh, ensure_ascii=False, indent=1)

    al = res[res["eligible"] & (res["ad"] > ACT_MAX) & (res["ad"] <= ALARM_MAX) & (res["p_avg3"] >= pmin)]
    al = pd.concat([al[al["setup"] == "long"].sort_values("p_avg3", ascending=False).head(6),
                    al[al["setup"] == "short"].sort_values("p_avg3", ascending=False).head(4)])
    alarm = []
    for _, r in al.iterrows():
        a = _pack(r, model)
        a["alarm_at"] = round(float(r["zone_hi"] if r["setup"] == "long" else r["zone_lo"]), 2)
        alarm.append(a)
    return {"asof": asof, "version": "v3.2 Phasen",
            "thresholds": {"p_min_long": P_MIN, "p_min_short": P_MIN_SHORT, "act_max_pct": ACT_MAX},
            "picks": picks, "removed": removed, "alarm": alarm,
            "base_rate": round(float(model.get("base_rate", np.nan)) * 100, 1),
            "model_metrics": model.get("metrics_out_of_sample")}
