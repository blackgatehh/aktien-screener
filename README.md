# Aktien-Screener (Framework „Aktien Analyse v2“)

Screent jeden Handelstag rund 700 Aktien aus **DAX, MDAX, Euro Stoxx 50, Nasdaq-100 und S&P 500**
und bewertet sie nach dem Framework aus dem Claude-Projekt „Aktien Analyse“.

## Ablauf

1. **GitHub Actions** (kostenlos) läuft Mo–Fr um 22:20 Uhr MEZ, nach US-Börsenschluss:
   - aktuelle Indexmitglieder von Wikipedia (Fallback: `data/universe.csv`)
   - 2 Jahre Tageskerzen pro Titel über `yfinance`
   - Indikatoren: EMA 5/13/20/50, SMA 200 inkl. Steigung, ATR, RSI, 52W-Hoch/-Tief, relative Stärke zum Index
   - **Zonen:** Zickzack-Wendepunkte → letzte abgeschlossene Bewegung → Fibonacci 50–61,8 % als Kauf- bzw. Short-Zone, Stop = Zonenrand ± 1 ATR, T1 = Bewegungsende, T2 = 1,272-Extension
   - **Kurslücken:** alle offenen Gaps der letzten 120 Tage, nächste Lücke darunter und darüber
   - **Kerzen:** Hammer, Shooting Star, bullisches und bärisches Engulfing am letzten Tag
   - **Fundamentaldaten** (sonntags): Bewertung und Qualität nach Framework
   - **Setup-Score 0–100** (Trend 25 · Zone 25 · Konfluenz 15 · Auslöser 15 · CRV 10 · Fundamentaldaten 10, Abschlag bei unpassendem Marktumfeld) und Note A–D
2. Ergebnisse landen in `data/`. `signals_log.csv` sammelt alle A/B-Signale, damit sich die Trefferquote später auswerten lässt.
3. **Claude** liest um 7:29 Uhr (Morgenbericht) und um 22:50 Uhr (Abend-Update) die Ergebnisse, prüft für die besten Kandidaten Nachrichten und Termine, aktualisiert das Dashboard und schickt eine Push-Nachricht.

## Dateien

| Datei | Inhalt |
|---|---|
| `screener.py` | Hauptlauf, Scores, Ausgabe |
| `indicators.py` | Technik: EMA, ATR, RSI, Zickzack, Fibonacci-Swing, Gaps, Kerzen |
| `universe.py` | Indexmitglieder und Benchmark-Zuordnung |
| `.github/workflows/screener.yml` | Zeitplan und Ausführung |
| `data/screener_latest.json` | Top-Long, Top-Short, Ausbrüche, Gap-Kandidaten, Marktumfeld |
| `data/screener_latest.csv` | alle Titel mit allen Kennzahlen |
| `data/charts_latest.json` | 180 Tageskerzen + EMA20/50 + SMA200 der Top-Kandidaten |

## Manuell starten

GitHub → Actions → „Aktien-Screener“ → „Run workflow“ (Häkchen bei „Fundamentaldaten neu laden“ beim ersten Lauf).

## Grenzen

- Die Zonen kommen aus einer Formel (Zickzack + Fibonacci), nicht aus einer Elliott-Zählung. Sie sind ein Vorfilter, die Feinanalyse macht Claude.
- Gewinnrevisionen und Insiderdaten liefert `yfinance` nicht zuverlässig. Claude prüft sie für die Top-Kandidaten per Websuche.
- Eine Kurslücke *muss* nicht geschlossen werden. Gaps sind ein Faktor im Score, kein Signal für sich.
- Keine Anlageberatung.
