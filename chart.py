"""Chartanalyse für Screener und Backtest (Framework v3).

Alles, was hier berechnet wird, nutzt nur Daten bis zum jeweiligen Tag. Damit liefern Live-Screener
und Backtest exakt dieselben Werte, und die Wahrscheinlichkeiten aus dem Backtest passen zum Live-Signal.

Inhalt
- EMA 5/13/20/50/200, deren Reihenfolge ("Fächer"), Steigungen und Kreuzungen
- Trendfilter: Long nur über EMA 200 mit EMA 50 > EMA 200, Short spiegelbildlich
- Fibonacci-Setup (Swing per Zickzack, Zone 50–61,8 %, Stop 1 ATR hinter der Zone, Ziel 1 = Swing-Extrem)
- Merkmale (Features) für das Wahrscheinlichkeitsmodell
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EMAS = (5, 13, 20, 50, 200)


# ------------------------------------------------------------------ Grundlagen
def _ema(a: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(a).ewm(span=n, adjust=False).mean().values


def chart_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Tageswerte aller Chart-Kennzahlen (vektorisiert)."""
    o, h, l, c = (df[k].values.astype(float) for k in ("Open", "High", "Low", "Close"))
    out = pd.DataFrame(index=df.index)
    out["open"], out["high"], out["low"], out["close"] = o, h, l, c
    prev = np.r_[c[0], c[:-1]]
    tr = np.maximum.reduce([h - l, np.abs(h - prev), np.abs(l - prev)])
    out["atr"] = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().values
    for n in EMAS:
        out[f"ema{n}"] = _ema(c, n)
    out["sma200"] = pd.Series(c).rolling(200).mean().values
    e = [out[f"ema{n}"].values for n in EMAS]
    # Fächer: +1 je korrekt geordnetem Nachbarpaar (5>13>20>50>200), −1 je umgekehrtem → −4 … +4
    out["stack"] = sum(np.sign(e[i] - e[i + 1]) for i in range(len(e) - 1))
    out["slope200"] = (out["ema200"] / out["ema200"].shift(20) - 1) * 100       # % über 20 Tage
    out["slope50"] = (out["ema50"] / out["ema50"].shift(10) - 1) * 100         # % über 10 Tage
    out["d200_atr"] = (c - out["ema200"]) / out["atr"]                           # Abstand zur EMA 200 in ATR
    out["d50_atr"] = (c - out["ema50"]) / out["atr"]

    def since_cross(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Tage seit der letzten Kreuzung a/b, mit Vorzeichen der aktuellen Lage (+ = a über b)."""
        s = np.sign(a - b)
        res = np.full(len(a), np.nan)
        last = -1
        for i in range(1, len(a)):
            if s[i] != s[i - 1] and s[i] != 0:
                last = i
            if last >= 0:
                res[i] = (i - last) * s[i]
        return res

    out["x5_13"] = since_cross(e[0], e[1])
    out["x20_50"] = since_cross(e[2], e[3])
    out["x50_200"] = since_cross(e[3], e[4])
    d = pd.Series(c).diff()
    up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    out["rsi"] = (100 - 100 / (1 + up / dn.replace(0, np.nan))).values
    out["rng_pct60"] = pd.Series((h - l) / c).rolling(60).mean().values * 100
    return out


def trend_class(r: pd.Series | dict) -> str:
    """Übergeordneter Trend aus EMA 50/200 und Kurslage."""
    c, e50, e200, sl = r["close"], r["ema50"], r["ema200"], r["slope200"]
    if c > e200 and e50 > e200 and sl >= 0:
        return "auf"
    if c < e200 and e50 < e200 and sl <= 0:
        return "ab"
    return "seitwärts"


def ema_text(r: pd.Series | dict) -> str:
    """Kurzbeschreibung des EMA-Bilds für Bericht und Dashboard."""
    names = [f"EMA{n}" for n in EMAS]
    vals = [r[f"ema{n}"] for n in EMAS]
    order = " > ".join(n for n, _ in sorted(zip(names, vals), key=lambda x: -x[1]))
    bits = [order.replace("EMA", "")]
    for key, lab, up, dn in (("x50_200", "50/200", "Golden Cross", "Death Cross"),
                             ("x20_50", "20/50", "20 über 50", "20 unter 50"),
                             ("x5_13", "5/13", "5 über 13", "5 unter 13")):
        v = r.get(key)
        if v is not None and np.isfinite(v) and abs(v) <= 10:
            bits.append(f"{up if v > 0 else dn} vor {int(abs(v))} T")
    return " · ".join(bits)


# ---------------------------------------------------------------- Swing / Fib
def zigzag_np(hi: np.ndarray, lo: np.ndarray, th: float) -> list[tuple[int, float, str]]:
    piv: list[tuple[int, float, str]] = []
    trend, ext_i, ext_hi, ext_lo, lo_i, hi_i = 0, 0, hi[0], lo[0], 0, 0
    for i in range(1, len(hi)):
        if trend == 0:
            if hi[i] > ext_hi:
                ext_hi, hi_i = hi[i], i
            if lo[i] < ext_lo:
                ext_lo, lo_i = lo[i], i
            if ext_hi >= ext_lo * (1 + th):
                if lo_i < hi_i:
                    piv.append((lo_i, ext_lo, "L"))
                    trend, ext_i = 1, hi_i
                else:
                    piv.append((hi_i, ext_hi, "H"))
                    trend, ext_i = -1, lo_i
        elif trend == 1:
            if hi[i] > ext_hi:
                ext_hi, ext_i = hi[i], i
            elif lo[i] <= ext_hi * (1 - th):
                piv.append((ext_i, ext_hi, "H"))
                trend, ext_lo, ext_i = -1, lo[i], i
        else:
            if lo[i] < ext_lo:
                ext_lo, ext_i = lo[i], i
            elif hi[i] >= ext_lo * (1 + th):
                piv.append((ext_i, ext_lo, "L"))
                trend, ext_hi, ext_i = 1, hi[i], i
    if trend == 1:
        piv.append((ext_i, ext_hi, "H"))
    elif trend == -1:
        piv.append((ext_i, ext_lo, "L"))
    return piv


def setup_at(f: pd.DataFrame, t: int, lookback: int = 260) -> dict | None:
    """Fibonacci-Setup am Tag t (Position im Frame aus chart_frame)."""
    if t < 220:
        return None
    s = max(0, t - lookback + 1)
    hi, lo = f["high"].values[s:t + 1], f["low"].values[s:t + 1]
    last, a = f["close"].values[t], f["atr"].values[t]
    rp = f["rng_pct60"].values[t]
    if not np.isfinite(rp):
        return None
    piv = zigzag_np(hi, lo, max(7.0, 4.5 * rp) / 100)
    if len(piv) < 2:
        return None

    def retr(p, q):
        return (q[1] - last) / (q[1] - p[1]) if q[1] != p[1] else np.nan

    cands = [(piv[-2], piv[-1])] + ([(piv[-3], piv[-2])] if len(piv) >= 3 else [])
    inside = [cd for cd in cands if 0 <= retr(*cd) <= 1]
    p1, p2 = max(inside, key=lambda cd: abs(cd[1][1] - cd[0][1])) if inside else cands[0]
    up = p2[2] == "H"
    H, L = (p2[1], p1[1]) if up else (p1[1], p2[1])
    hi_i, lo_i = (p2[0], p1[0]) if up else (p1[0], p2[0])
    rng = H - L
    if rng < 4 * a:
        return None
    if up:  # Long: Rücksetzer in Aufwärtsbewegung
        zlo, zhi = H - 0.618 * rng, H - 0.5 * rng
        stop, t1, t2 = zlo - a, H, L + 1.272 * rng
        dist = 0.0 if zlo <= last <= zhi else ((last / zhi - 1) * 100 if last > zhi else (last / zlo - 1) * 100)
        broken = last <= stop or last >= t1
        retrace = (H - last) / rng
    else:   # Short: Gegenbewegung in Abwärtsbewegung
        zlo, zhi = L + 0.5 * rng, L + 0.618 * rng
        stop, t1, t2 = zhi + a, L, H - 1.272 * rng
        dist = 0.0 if zlo <= last <= zhi else ((last / zlo - 1) * 100 if last < zlo else (last / zhi - 1) * 100)
        broken = last >= stop or last <= t1
        retrace = (last - L) / rng
    entry = last if zlo <= last <= zhi else (zlo + zhi) / 2
    risk = abs(entry - stop)
    crv = abs(t1 - entry) / risk if risk > 0 else np.nan
    return {"setup": "long" if up else "short", "zone_lo": zlo, "zone_hi": zhi, "stop": stop, "t1": t1, "t2": t2,
            "entry": entry, "crv_entry": crv, "zone_dist_pct": dist, "broken": bool(broken), "retrace": retrace,
            "swing_high": H, "swing_low": L, "hi_idx": s + hi_i, "lo_idx": s + lo_i,
            "bars_since_extreme": t - (s + (hi_i if up else lo_i)), "t1_atr": abs(t1 - entry) / a if a > 0 else np.nan}


def candle_at(f: pd.DataFrame, t: int) -> str:
    o, h, l, c = (f[k].values[t] for k in ("open", "high", "low", "close"))
    po, pc, a = f["open"].values[t - 1], f["close"].values[t - 1], f["atr"].values[t]
    rng = h - l
    if rng <= 0:
        return ""
    body, lower, upper = abs(c - o), min(o, c) - l, h - max(o, c)
    big = rng >= 0.6 * a
    if big and lower >= 2 * body and upper <= max(body, 0.15 * rng) and (c - l) / rng >= 0.6:
        return "hammer"
    if big and upper >= 2 * body and lower <= max(body, 0.15 * rng) and (h - c) / rng >= 0.6:
        return "shooting_star"
    if pc < po and c > o and c >= po and o <= pc:
        return "bull_engulfing"
    if pc > po and c < o and c <= po and o >= pc:
        return "bear_engulfing"
    return ""


# ------------------------------------------------------------------- Merkmale
FEATURES = ["trend_aligned", "trend_against", "stack", "slope200", "d200_atr", "x50_200_aligned", "x20_50_aligned",
            "x5_13_turn", "retrace", "zone_in", "zone_dist_abs", "conf_ema", "trigger", "rsi_turn", "rsi_side",
            "crv", "t1_atr", "atr_pct", "bars_since_extreme", "bench_aligned", "is_short"]


def features(f: pd.DataFrame, t: int, st: dict, bench_side: float = 0.0) -> dict:
    """Modellmerkmale eines Setups. Alle Richtungsgrößen sind so gedreht, dass + = für den Trade."""
    r = f.iloc[t]
    s = 1.0 if st["setup"] == "long" else -1.0
    tc = trend_class(r)
    zlo, zhi = st["zone_lo"] * 0.985, st["zone_hi"] * 1.015
    conf = sum(1 for k in ("ema50", "ema200") if zlo <= r[k] <= zhi)
    cnd = candle_at(f, t)
    trig = (s > 0 and cnd in ("hammer", "bull_engulfing")) or (s < 0 and cnd in ("shooting_star", "bear_engulfing"))
    rsi5 = f["rsi"].values[t - 5]
    rsi_turn = (s > 0 and rsi5 < 45 and r["rsi"] > rsi5) or (s < 0 and rsi5 > 55 and r["rsi"] < rsi5)

    def aligned(v):  # Kreuzung in Tradingrichtung: + Tage seit Kreuzung → 1, dagegen → −1
        return 0.0 if not np.isfinite(v) else float(np.sign(v) * s)

    x513 = r["x5_13"]
    return {
        "trend_aligned": float((tc == "auf" and s > 0) or (tc == "ab" and s < 0)),
        "trend_against": float((tc == "ab" and s > 0) or (tc == "auf" and s < 0)),
        "stack": s * r["stack"] / 4,
        "slope200": float(np.clip(s * r["slope200"], -10, 10)),
        "d200_atr": float(np.clip(s * r["d200_atr"], -10, 10)),
        "x50_200_aligned": aligned(r["x50_200"]),
        "x20_50_aligned": aligned(r["x20_50"]),
        "x5_13_turn": float(np.isfinite(x513) and np.sign(x513) == s and abs(x513) <= 3),
        "retrace": float(st["retrace"]),
        "zone_in": float(st["zone_dist_pct"] == 0),
        "zone_dist_abs": float(min(abs(st["zone_dist_pct"]), 10)),
        "conf_ema": float(conf),
        "trigger": float(trig),
        "rsi_turn": float(rsi_turn),
        "rsi_side": float(s * (r["rsi"] - 50) / 50),
        "crv": float(np.clip(st["crv_entry"], 0, 8)),
        "t1_atr": float(np.clip(st["t1_atr"], 0, 20)),
        "atr_pct": float(r["atr"] / r["close"] * 100),
        "bars_since_extreme": float(min(st["bars_since_extreme"], 120)),
        "bench_aligned": float(s * bench_side),
        "is_short": float(s < 0),
    }


def trend_ok(st: dict, r: pd.Series | dict) -> bool:
    """Harter Trendfilter (Framework v3): nur mit dem übergeordneten EMA-Trend handeln."""
    tc = trend_class(r)
    return (st["setup"] == "long" and tc == "auf") or (st["setup"] == "short" and tc == "ab")


def bench_side_series(bench: pd.DataFrame | None, index: pd.Index) -> pd.Series:
    """+1, wenn der Vergleichsindex über seiner EMA 200 notiert, sonst −1 (auf die Tage des Titels gelegt)."""
    if bench is None or len(bench) < 220:
        return pd.Series(0.0, index=index)
    c = bench["Close"]
    side = np.sign(c - c.ewm(span=200, adjust=False).mean())
    return side.reindex(index, method="ffill").fillna(0.0)


# ------------------------------------------------------------ Modell anwenden
def predict(model: dict | None, feat: dict) -> float:
    """Wahrscheinlichkeit T1 vor Stop (logistisches Modell aus backtest.py)."""
    if not model:
        return np.nan
    x = np.array([feat[k] for k in model["features"]], dtype=float)
    z = (x - np.array(model["mean"])) / np.array(model["std"])
    logit = float(model["intercept"] + np.dot(model["coef"], z))
    return 1 / (1 + np.exp(-logit))
