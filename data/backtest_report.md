# Backtest Fibonacci-Setups · 2026-11-22 08:30 UTC

Zeitraum 6y, 623 Titel, 162,441 Signaltage aus 16,495 Setups. Limit-Ausführungsquote 62 %. Gewinn = Ziel 1 (= 1 R, Abstand wie der Stop) vor dem Stop innerhalb von 60 Handelstagen. Altes Ziel (Swing-Extrem) erreichen nur 21.8 %.

**Basisquote:** 49.6 % aller ausgeführten Setups erreichen Ziel 1 vor dem Stop.

**Modellgüte außerhalb der Trainingszeit** (ab 2025-11-19, 31,135 Signale): AUC 0.543 (0,5 = Zufall), Brier 0.249.
**Schwellen:** Aufnahme in die Top 10 ab 56%, Verbleib bis 52%.

## Trefferquote nach übergeordnetem Trend (EMA 50/200)
Long im Aufwärtstrend bzw. Short im Abwärtstrend = mit dem Trend.

| rt                  |     n |   setups |   trefferquote |   avg_R |
|:--------------------|------:|---------:|---------------:|--------:|
| gegen Trend · long  | 16093 |     2246 |           51.9 |    0.03 |
| gegen Trend · short | 34056 |     4270 |           47.3 |   -0.06 |
| mit Trend · long    | 42027 |     5079 |           54.2 |    0.08 |
| mit Trend · short   | 35790 |     4027 |           47   |   -0.07 |
| seitwärts · long    | 15272 |     2777 |           52.5 |    0.05 |
| seitwärts · short   | 19203 |     3107 |           44.4 |   -0.12 |

## Trefferquote nach EMA-Fächer (5>13>20>50>200, in Tradingrichtung, −1 … +1)

| stack        |     n |   setups |   trefferquote |   avg_R |
|:-------------|------:|---------:|---------------:|--------:|
| klar dagegen | 68788 |    10191 |           49.2 |   -0.02 |
| eher dagegen | 49150 |    10180 |           48.7 |   -0.03 |
| eher dafür   | 28592 |     7883 |           49.8 |   -0.01 |
| klar dafür   | 15911 |     4369 |           54   |    0.08 |

## Umkehrkerze am Signaltag

|   trigger |      n |   setups |   trefferquote |   avg_R |
|----------:|-------:|---------:|---------------:|--------:|
|         0 | 149748 |    16309 |           49.6 |   -0.01 |
|         1 |  12693 |     7412 |           50.4 |    0    |

## Kalibrierung außerhalb der Trainingszeit (vorhergesagt vs. eingetreten)

| p             |     n |   setups |   trefferquote |   avg_R |
|:--------------|------:|---------:|---------------:|--------:|
| (-0.001, 0.4] |    49 |       23 |           51   |   -0.02 |
| (0.4, 0.45]   |  3138 |      911 |           44.6 |   -0.12 |
| (0.45, 0.5]   | 12997 |     2057 |           46.7 |   -0.07 |
| (0.5, 0.55]   | 11789 |     1960 |           53.3 |    0.06 |
| (0.55, 0.6]   |  3047 |      779 |           54.8 |    0.1  |
| (0.6, 0.65]   |   115 |       58 |           52.2 |    0.03 |

## Modellgewichte (standardisiert, + = erhöht die Wahrscheinlichkeit)

|                    |   Gewicht |
|:-------------------|----------:|
| is_short           |    -0.151 |
| retrace            |    -0.109 |
| ext_atr            |    -0.064 |
| x20_50_aligned     |    -0.061 |
| bench_aligned      |    -0.054 |
| t1_atr             |    -0.036 |
| x50_200_aligned    |    -0.034 |
| rs126              |    -0.026 |
| rsi2_side          |    -0.021 |
| d200_atr           |    -0.019 |
| rsi_side           |    -0.018 |
| conf_ema           |    -0.017 |
| x5_13_turn         |    -0.015 |
| zone_dist_abs      |    -0.011 |
| atr_pct            |    -0.002 |
| rsi_turn           |    -0.001 |
| trigger            |     0.01  |
| slope200           |     0.017 |
| crv                |     0.034 |
| trend_against      |     0.041 |
| zone_in            |     0.043 |
| trend_aligned      |     0.048 |
| bars_since_extreme |     0.06  |
| stack              |     0.065 |

Hinweis: heutiges Index-Universum (Survivorship Bias), Gebühren und Spreads nicht berücksichtigt.
