"""Zeichnet die Top-10-Übersicht des Tagesberichts als Bild (für Push/Chat) – im Stil des Beispielberichts.

Aufruf:  python render_report.py [data/claude_report.json] [data/report_latest.png]

Erwartet in claude_report.json je Eintrag in "picks":
  rank, ticker, name, isin, wkn (optional), setup ("long"/"short"), category,
  probability (0–100, Gewinnwahrscheinlichkeit T1 vor Stop), confidence (0–100, Belastbarkeit),
  status_report ("neu"/"bleibt"), in_report_since (YYYY-MM-DD), ema_text, trend,
  close, currency, zone_lo, zone_hi, stop, t1, t2 (optional), crv, weeks (Text), instrument,
  comment, risks
Optional auf oberster Ebene: base_rate (%), removed: [{name, reason}]
"""
from __future__ import annotations

import json
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

INK, MUTED, LINE, CARD, BG = "#16161a", "#6b6a66", "#dcdad3", "#f4f3ef", "#ffffff"
BLUE, RED, GOLD, GREEN = "#2a63d6", "#d03b3b", "#c9961a", "#1a8a4a"
CAT = {  # Hintergrund, Schrift
    "Einstieg jetzt": ("#e3f2e8", "#1a6b3a"),
    "Limit setzen": ("#e6eefb", "#1f4fa8"),
    "Beobachten": ("#fbf0dc", "#8a5a0b"),
    "Offene Position": ("#ecebe6", "#52514e"),
}
SYM = {"USD": "$", "EUR": "€", "GBP": "£", "CHF": "CHF "}


def money(v: float, cur: str = "") -> str:
    if v is None:
        return "–"
    d = 0 if abs(v) >= 1000 else 2
    s = f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sym = SYM.get(cur or "", "")
    return f"{sym}{s}" if sym == "$" else f"{s} {sym}".strip()


def pct(v: float) -> str:
    return (f"{v:+.1f} %").replace(".", ",")


def chip(ax, x, y, text, bg, fg, size=8.5):
    t = ax.text(x, y, f" {text} ", fontsize=size, color=fg, va="center", ha="left", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.28,rounding_size=0.6", fc=bg, ec="none"))
    return t


def render(report: dict, out: str) -> None:
    picks = sorted(report.get("picks", []), key=lambda p: p.get("rank", 99))[:10]
    n = len(picks)
    row_h = 1.3
    head = 1.35
    removed = report.get("removed") or []
    foot = 0.5 + (0.22 * min(len(removed), 6) + 0.3 if removed else 0)
    H = head + n * row_h + foot
    fig = plt.figure(figsize=(10.5, H), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 10.5)
    ax.set_ylim(0, H)
    ax.axis("off")
    fig.patch.set_facecolor(BG)

    # Kopf
    ax.text(0.3, H - 0.42, f"Top 10 Trade-Chancen · {report.get('date', '')}", fontsize=15, fontweight="bold", color=INK, va="center")
    ax.text(0.3, H - 0.82, report.get("market_line", ""), fontsize=9.5, color=MUTED, va="center")
    br = report.get("base_rate")
    ax.text(10.2, H - 0.42, f"Basisquote aller Setups {br:.0f} %".replace(".", ",") if br else "", fontsize=8,
            color=MUTED, va="center", ha="right")

    for i, p in enumerate(picks):
        top = H - head - i * row_h
        y0 = top - row_h + 0.08
        ax.add_patch(FancyBboxPatch((0.2, y0), 10.1, row_h - 0.14, boxstyle="round,pad=0,rounding_size=0.12",
                                    fc=CARD, ec="none"))
        cy = y0 + (row_h - 0.14) / 2
        cur = p.get("currency", "")
        longs = p.get("setup") == "long"

        # Rang
        ax.text(0.5, cy, str(p.get("rank", i + 1)), fontsize=15, color=MUTED, ha="center", va="center")

        # Name, Kennung, Chips
        name = p.get("name") or p.get("ticker")
        if len(name) > 30:
            name = re.sub(r",?\s+(Inc|Incorporated|Corporation|Corp|Company|Co|plc|SE|AG|N\.V|S\.A)\.?$", "", name)
        if len(name) > 30:
            name = name[:29] + "…"
        ax.text(0.85, cy + 0.33, name, fontsize=11, fontweight="bold", color=INK, va="center")
        ident = " · ".join(x for x in [
            f"ISIN {p['isin']}" if p.get("isin") else "",
            f"WKN {p['wkn']}" if p.get("wkn") else "",
            p.get("ticker", ""),
            (f"im Bericht seit {p['in_report_since'][8:10]}.{p['in_report_since'][5:7]}."
             if p.get("status_report") == "bleibt" and p.get("in_report_since") else "neu im Bericht")] if x)
        ax.text(0.85, cy + 0.03, ident, fontsize=7.8, color=MUTED, va="center")
        chip(ax, 0.85, cy - 0.3, "Long" if longs else "Short", "#e3f2e8" if longs else "#fbe4e4",
             GREEN if longs else RED)
        bg, fg = CAT.get(p.get("category", ""), ("#ecebe6", "#52514e"))
        chip(ax, 1.62, cy - 0.3, p.get("category", ""), bg, fg)

        # Wahrscheinlichkeit, Confidence, Eckdaten
        cx = 4.3
        prob = float(p.get("probability", 0) or 0)
        conf = float(p.get("confidence", 0) or 0)
        ax.text(cx, cy + 0.4, f"Wahrscheinlichkeit {prob:.0f} %", fontsize=9.5, color=INK, va="center", fontweight="bold")
        ax.add_patch(FancyBboxPatch((cx, cy + 0.17), 1.9, 0.09, boxstyle="round,pad=0,rounding_size=0.04", fc=LINE, ec="none"))
        ax.add_patch(FancyBboxPatch((cx, cy + 0.17), 1.9 * prob / 100, 0.09, boxstyle="round,pad=0,rounding_size=0.04",
                                    fc=GREEN, ec="none"))
        ax.text(cx, cy - 0.02, f"Confidence {conf:.0f}/100", fontsize=8.3, color=INK, va="center")
        ax.add_patch(FancyBboxPatch((cx + 1.15, cy - 0.05), 0.75, 0.06, boxstyle="round,pad=0,rounding_size=0.03", fc=LINE, ec="none"))
        ax.add_patch(FancyBboxPatch((cx + 1.15, cy - 0.05), 0.75 * conf / 100, 0.06, boxstyle="round,pad=0,rounding_size=0.03",
                                    fc=BLUE, ec="none"))
        crv = p.get("crv")
        crv_s = f"{float(crv):.1f}".replace(".", ",") if crv is not None else "–"
        ax.text(cx, cy - 0.22, f"CRV bis T2 {crv_s} · T1 {p.get('weeks', '')}", fontsize=8.2, color=MUTED, va="center")
        ax.text(cx, cy - 0.41, str(p.get("instrument", "")), fontsize=8.2, color=MUTED, va="center")

        # Zonen-Leiste
        lx0, lx1 = 6.6, 10.05
        px, st, zl, zh, t1 = (float(p[k]) for k in ("close", "stop", "zone_lo", "zone_hi", "t1"))
        t2 = float(p["t2"]) if p.get("t2") is not None else None
        pts = [st, zl, zh, px, t1] + ([t2] if t2 is not None else [])
        lo, hi = min(pts), max(pts)
        pad = (hi - lo) * 0.07 or 1
        X = lambda v: lx0 + (v - lo + pad) / (hi - lo + 2 * pad) * (lx1 - lx0)  # noqa: E731
        ly = cy + 0.22
        ax.plot([lx0, lx1], [ly, ly], color=LINE, lw=2, solid_capstyle="round")
        ax.add_patch(plt.Rectangle((X(zl), ly - 0.07), X(zh) - X(zl), 0.14, color=BLUE, alpha=0.35, lw=0))
        ax.plot([X(st)] * 2, [ly - 0.12, ly + 0.12], color=RED, lw=2.2)
        ax.plot([X(t1)] * 2, [ly - 0.12, ly + 0.12], color=GOLD, lw=2.2)
        if t2 is not None:
            ax.plot([X(t2)] * 2, [ly - 0.09, ly + 0.09], color=GOLD, lw=1.4, alpha=0.55)
        ax.plot(X(px), ly, "o", ms=7.5, color="#3d3c39", mec=CARD, mew=1.6, zorder=5)
        ref = px if zl <= px <= zh else (zl + zh) / 2
        d_st = (st / ref - 1) * 100
        d_t1 = (t1 / ref - 1) * 100
        ax.text(X(st), ly - 0.27, f"Stop {pct(d_st)}", fontsize=7.6, color=RED, ha="center", va="center")
        ax.text(X(t1), ly - 0.27, f"T1 {pct(d_t1)}", fontsize=7.6, color=GOLD, ha="center", va="center")
        if t2 is not None:
            ax.text(X(t2), ly + 0.24, f"T2 {pct((t2 / ref - 1) * 100)}", fontsize=7.2, color=GOLD, alpha=0.8,
                    ha="center", va="center")
        ax.text(lx0, cy - 0.3, f"Kurs {money(px, cur)} · Zone {money(zl, cur)}–{money(zh, cur)}", fontsize=8,
                color=INK, va="center")
        if p.get("ema_text"):
            ax.text(lx0, cy - 0.47, f"EMA {p['ema_text']}"[:62], fontsize=7.2, color=MUTED, va="center")

    # Raus seit dem letzten Bericht
    y = 0.66 + 0.22 * min(len(removed), 6)
    if removed:
        ax.text(0.3, y, "Raus seit dem letzten Bericht:", fontsize=8.5, color=INK, va="center", fontweight="bold")
        for k, r in enumerate(removed[:6]):
            ax.text(0.3, y - 0.22 * (k + 1), f"– {r.get('name') or r.get('ticker')}: {r.get('reason', '')}",
                    fontsize=8, color=MUTED, va="center")
    # Legende
    ax.text(0.3, 0.26, "Wahrscheinlichkeit = Trefferquote vergleichbarer Setups im Backtest (Ziel 1 vor Stop). "
            "Confidence = Belastbarkeit (Fallzahl, Tage stabil, EMA-Bild, Termine, News).",
            fontsize=7.4, color=MUTED, va="center")
    ax.text(0.3, 0.1, "Leiste: blau = Einstiegszone · rot = Stop · gold = Ziel 1 (1 R) · hellgold = Ziel 2 (altes Hoch/Tief) · Punkt = Kurs. "
            "Prozent ab Einstieg (Kurs in der Zone, sonst Zonenmitte). Keine Anlageberatung.",
            fontsize=7.4, color=MUTED, va="center")
    fig.savefig(out, facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data/claude_report.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else "data/report_latest.png"
    with open(src, encoding="utf-8") as fh:
        render(json.load(fh), dst)
    print(f"Bild geschrieben: {dst}")
