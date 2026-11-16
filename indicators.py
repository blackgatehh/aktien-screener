"""Technische Bausteine für den Screener (alle Funktionen arbeiten auf OHLCV-DataFrames)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev = df["Close"].shift(1)
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - prev).abs(), (df["Low"] - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def lin(x: float, best: float, worst: float) -> float:
    """Linear auf 0–100 skalieren (best → 100, worst → 0), abgeschnitten."""
    if x is None or not np.isfinite(x):
        return np.nan
    return float(np.clip((x - worst) / (best - worst) * 100, 0, 100))


def zigzag(df: pd.DataFrame, threshold_pct: float) -> list[tuple[int, float, str]]:
    """Wendepunkte (Index, Kurs, 'H'/'L'), bestätigt nach einer Gegenbewegung von threshold_pct %."""
    hi, lo = df["High"].values, df["Low"].values
    th = threshold_pct / 100
    pivots: list[tuple[int, float, str]] = []
    trend = 0  # 1 = aufwärts (suche Hoch), -1 = abwärts (suche Tief)
    ext_i, ext_hi, ext_lo = 0, hi[0], lo[0]
    lo_i = hi_i = 0
    for i in range(1, len(df)):
        if trend == 0:
            if hi[i] > ext_hi:
                ext_hi, hi_i = hi[i], i
            if lo[i] < ext_lo:
                ext_lo, lo_i = lo[i], i
            if ext_hi >= ext_lo * (1 + th):
                if lo_i < hi_i:
                    pivots.append((lo_i, ext_lo, "L"))
                    trend, ext_i, ext_hi = 1, hi_i, ext_hi
                else:
                    pivots.append((hi_i, ext_hi, "H"))
                    trend, ext_i, ext_lo = -1, lo_i, ext_lo
        elif trend == 1:
            if hi[i] > ext_hi:
                ext_hi, ext_i = hi[i], i
            elif lo[i] <= ext_hi * (1 - th):
                pivots.append((ext_i, ext_hi, "H"))
                trend, ext_lo, ext_i = -1, lo[i], i
        else:
            if lo[i] < ext_lo:
                ext_lo, ext_i = lo[i], i
            elif hi[i] >= ext_lo * (1 + th):
                pivots.append((ext_i, ext_lo, "L"))
                trend, ext_hi, ext_i = 1, hi[i], i
    # letzter, noch unbestätigter Extrempunkt
    if trend == 1:
        pivots.append((ext_i, ext_hi, "H"))
    elif trend == -1:
        pivots.append((ext_i, ext_lo, "L"))
    return pivots


def swing(df: pd.DataFrame, lookback: int = 260) -> dict | None:
    """Letzte abgeschlossene Bewegung (Wendepunkt → Wendepunkt), gegen die der Kurs gerade korrigiert.

    Schwelle: 4,5 × durchschnittliche Tagesspanne in %, mindestens 7 %.
    """
    d = df.tail(lookback)
    if len(d) < 80:
        return None
    rng_pct = float(((d["High"] - d["Low"]) / d["Close"]).tail(60).mean() * 100)
    piv = zigzag(d, max(7.0, 3.0 * rng_pct * 1.5))
    if len(piv) < 2:
        return None
    last = float(d["Close"].iloc[-1])

    def retrace(a, b) -> float:  # Anteil, um den der Kurs die Bewegung a→b zurückgelaufen ist
        return (b[1] - last) / (b[1] - a[1]) if b[1] != a[1] else np.nan

    # Der letzte Wendepunkt ist der laufende Extrempunkt der aktuellen Korrektur.
    # Relevante Bewegung ist daher die davor (piv[-3] → piv[-2]). Ist sie schon überschritten
    # (Trend läuft weiter) oder ganz zurückgelaufen (Trendwechsel), gilt die jüngste Bewegung.
    if len(piv) >= 3 and 0 <= retrace(piv[-3], piv[-2]) <= 1:
        (i1, p1, k1), (i2, p2, k2) = piv[-3], piv[-2]
    else:
        (i1, p1, k1), (i2, p2, k2) = piv[-2], piv[-1]
    H, L = (p2, p1) if k2 == "H" else (p1, p2)
    hi_i, lo_i = (i2, i1) if k2 == "H" else (i1, i2)
    return {
        "high": float(H), "high_date": d.index[hi_i].strftime("%Y-%m-%d"),
        "low": float(L), "low_date": d.index[lo_i].strftime("%Y-%m-%d"),
        "direction": "up" if k2 == "H" else "down",  # Richtung der Bewegung, gegen die korrigiert wird
    }


def open_gaps(df: pd.DataFrame, lookback: int = 120, min_pct: float = 0.003) -> list[dict]:
    """Offene (ganz oder teilweise ungeschlossene) Kurslücken der letzten `lookback` Tage."""
    d = df.tail(lookback + 1)
    hi, lo = d["High"].values, d["Low"].values
    gaps = []
    for i in range(1, len(d)):
        after_lo = lo[i + 1:].min() if i + 1 < len(d) else np.inf
        after_hi = hi[i + 1:].max() if i + 1 < len(d) else -np.inf
        if lo[i] > hi[i - 1] * (1 + min_pct):  # Gap nach oben -> Lücke liegt darunter
            bottom, top = hi[i - 1], min(lo[i], after_lo)
            if top > bottom:
                gaps.append({"type": "up", "from": float(bottom), "to": float(top),
                             "date": d.index[i].strftime("%Y-%m-%d")})
        elif hi[i] < lo[i - 1] * (1 - min_pct):  # Gap nach unten -> Lücke liegt darüber
            bottom, top = max(hi[i], after_hi), lo[i - 1]
            if top > bottom:
                gaps.append({"type": "down", "from": float(bottom), "to": float(top),
                             "date": d.index[i].strftime("%Y-%m-%d")})
    return gaps


def candle(df: pd.DataFrame, atr_last: float) -> str:
    """Umkehrkerze am letzten Tag erkennen."""
    if len(df) < 2:
        return ""
    o, h, l, c = (float(df[k].iloc[-1]) for k in ("Open", "High", "Low", "Close"))
    po, pc = float(df["Open"].iloc[-2]), float(df["Close"].iloc[-2])
    rng = h - l
    if rng <= 0:
        return ""
    body = abs(c - o)
    lower = min(o, c) - l
    upper = h - max(o, c)
    big = rng >= 0.6 * atr_last
    if big and lower >= 2 * body and upper <= max(body, 0.15 * rng) and (c - l) / rng >= 0.6:
        return "hammer"
    if big and upper >= 2 * body and lower <= max(body, 0.15 * rng) and (h - c) / rng >= 0.6:
        return "shooting_star"
    if pc < po and c > o and c >= po and o <= pc:
        return "bull_engulfing"
    if pc > po and c < o and c <= po and o >= pc:
        return "bear_engulfing"
    return ""
