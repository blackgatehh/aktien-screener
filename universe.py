"""Aktien-Universum: DAX, MDAX, Euro Stoxx 50, Nasdaq-100, S&P 500.

Lädt die aktuellen Indexmitglieder von Wikipedia. Schlägt das fehl, wird
die zuletzt erfolgreich geladene Liste (data/universe.csv) bzw. die
eingebaute Startliste genutzt.
"""
from __future__ import annotations

import io
import os
import re

import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (aktien-screener; GitHub Actions)"}
UNIVERSE_FILE = os.path.join(os.path.dirname(__file__), "data", "universe.csv")

# Startliste, falls weder Wikipedia noch eine gespeicherte Liste verfügbar ist.
SEED = {
    "DAX": "ADS AIR ALV BAS BAYN BEI BMW BNR CBK CON DTG DBK DB1 DHL DTE EOAN FRE G1A HNR1 HEI HEN3 IFX MBG MRK MTX MUV2 P911 PAH3 QIA RHM RWE SAP SRT3 SIE ENR SHL SY1 VNA VOW3 ZAL".split(),
    "MDAX": "EVD AIXA BOSS KGX LEG LHA NEM PUM RAA TEG TKA UTDI WAF FRA FPE3 HOT HAG JEN KBX LXS AT1 BC8 DWNI EVK EVT FNTN GXI HFG HLE NDA R3NK RRTL SDF SIX2 STM TLX TMV 8TRA DHER DUE NDX1 PSM G24 AG1 1COV TKMS OHB".split(),
    "EUROSTOXX50": ["ASML.AS", "AD.AS", "INGA.AS", "PRX.AS", "WKL.AS", "ADYEN.AS", "MC.PA", "OR.PA", "RMS.PA",
                    "TTE.PA", "SAN.PA", "AI.PA", "SU.PA", "BNP.PA", "CS.PA", "DG.PA", "EL.PA", "SAF.PA", "AIR.PA",
                    "BN.PA", "RI.PA", "SGO.PA", "ITX.MC", "IBE.MC", "SAN.MC", "BBVA.MC", "ENEL.MI", "ENI.MI",
                    "ISP.MI", "UCG.MI", "RACE.MI", "STLAM.MI", "NOKIA.HE", "NDA-FI.HE", "ABI.BR"],
}

INDEX_BENCHMARK = {
    "DAX": "^GDAXI",
    "MDAX": "^MDAXI",
    "EUROSTOXX50": "^STOXX50E",
    "NASDAQ100": "^NDX",
    "SP500": "^GSPC",
}

# Endungen der Börsenplätze für Euro-Stoxx-Titel (Wikipedia nennt oft nur Kürzel + Land)
EXCHANGE_SUFFIX = {
    "Germany": ".DE", "France": ".PA", "Netherlands": ".AS", "Spain": ".MC", "Italy": ".MI",
    "Finland": ".HE", "Belgium": ".BR", "Ireland": ".IR", "Portugal": ".LS", "Austria": ".VI",
}


def _tables(url: str) -> list[pd.DataFrame]:
    html = requests.get(url, headers=UA, timeout=30).text
    out = []
    for df in pd.read_html(io.StringIO(html)):
        if isinstance(df.columns, pd.MultiIndex):  # mehrzeilige Kopfzeilen glätten
            df.columns = [" ".join(str(x) for x in col if "Unnamed" not in str(x)).strip() for col in df.columns]
        out.append(df)
    return out


def _pick_col(df: pd.DataFrame, names: list[str]) -> str | None:
    for col in df.columns:
        c = str(col).strip().lower()
        if any(c == n or c.startswith(n) for n in names):
            return col
    return None


def _yahoo_us(sym: str) -> str:
    return str(sym).strip().replace(".", "-")


def _clean(sym: str) -> str:
    return re.sub(r"\[.*?\]", "", str(sym)).strip()


def fetch_sp500() -> list[str]:
    for df in _tables("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"):
        col = _pick_col(df, ["symbol"])
        if col is not None and len(df) > 400:
            return [_yahoo_us(_clean(s)) for s in df[col]]
    raise RuntimeError("S&P 500 Tabelle nicht gefunden")


def fetch_nasdaq100() -> list[str]:
    for df in _tables("https://en.wikipedia.org/wiki/Nasdaq-100"):
        col = _pick_col(df, ["ticker", "symbol"])
        if col is not None and 95 <= len(df) <= 115:
            syms = [_yahoo_us(_clean(s)) for s in df[col] if str(s).strip() and str(s) != "nan"]
            if sum(s.isupper() for s in syms) >= 90:
                return syms
    raise RuntimeError("Nasdaq-100 Tabelle nicht gefunden")


def _fetch_german(url: str, min_len: int, max_len: int) -> list[str]:
    for df in _tables(url):
        col = _pick_col(df, ["ticker", "symbol"])
        if col is not None and min_len <= len(df) <= max_len:
            out = []
            for s in df[col]:
                s = _clean(s)
                if not s or s.lower() == "nan":
                    continue
                s = s.split(":")[-1].strip()
                out.append(s if "." in s else f"{s}.DE")
            return out
    raise RuntimeError(f"Tabelle nicht gefunden: {url}")


def fetch_dax() -> list[str]:
    return _fetch_german("https://en.wikipedia.org/wiki/DAX", 38, 45)


def fetch_mdax() -> list[str]:
    return _fetch_german("https://en.wikipedia.org/wiki/MDAX", 45, 55)


def fetch_eurostoxx50() -> list[str]:
    for df in _tables("https://en.wikipedia.org/wiki/EURO_STOXX_50"):
        col = _pick_col(df, ["ticker", "symbol"])
        if col is None or not (45 <= len(df) <= 55):
            continue
        country_col = _pick_col(df, ["country", "registered office", "headquarters"])
        out = []
        for _, row in df.iterrows():
            s = _clean(row[col])
            if "." in s:
                out.append(s)
                continue
            suffix = EXCHANGE_SUFFIX.get(str(row[country_col]).strip(), "") if country_col else ""
            if suffix:
                out.append(s + suffix)
        if len(out) >= 40:
            return out
    raise RuntimeError("Euro Stoxx 50 Tabelle nicht gefunden")


FETCHERS = {
    "DAX": fetch_dax,
    "MDAX": fetch_mdax,
    "EUROSTOXX50": fetch_eurostoxx50,
    "NASDAQ100": fetch_nasdaq100,
    "SP500": fetch_sp500,
}


def load_universe(refresh: bool = True) -> pd.DataFrame:
    """Gibt DataFrame mit Spalten ticker, indices (z. B. 'DAX|EUROSTOXX50') zurück."""
    saved = pd.read_csv(UNIVERSE_FILE) if os.path.exists(UNIVERSE_FILE) else None
    members: dict[str, set[str]] = {}
    for idx, fn in FETCHERS.items():
        tickers: list[str] = []
        if refresh:
            try:
                tickers = fn()
                print(f"[universe] {idx}: {len(tickers)} Titel live geladen")
            except Exception as exc:  # noqa: BLE001
                print(f"[universe] {idx}: Live-Abruf fehlgeschlagen ({exc}), nutze Fallback")
        if not tickers and saved is not None:
            tickers = saved.loc[saved["indices"].str.contains(idx), "ticker"].tolist()
        if not tickers and idx in SEED:
            tickers = [t if "." in t else f"{t}.DE" for t in SEED[idx]]
        for t in tickers:
            members.setdefault(t, set()).add(idx)
    df = pd.DataFrame(
        [{"ticker": t, "indices": "|".join(sorted(v))} for t, v in sorted(members.items())]
    )
    os.makedirs(os.path.dirname(UNIVERSE_FILE), exist_ok=True)
    if len(df) > 300:  # nur plausible Listen speichern
        df.to_csv(UNIVERSE_FILE, index=False)
    return df


def benchmark_for(indices: str) -> str:
    order = ["MDAX", "DAX", "EUROSTOXX50", "NASDAQ100", "SP500"]
    for idx in order:
        if idx in indices:
            # Nasdaq-Werte, die auch im S&P sind, gegen den S&P 500 messen
            if idx == "NASDAQ100" and "SP500" in indices:
                return INDEX_BENCHMARK["SP500"]
            return INDEX_BENCHMARK[idx]
    return "^GSPC"
