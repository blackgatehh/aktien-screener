# Backtest Fibonacci-Setups · 2026-11-19 10:37 UTC

Zeitraum 6y, 623 Titel, 162,212 Signaltage aus 16,468 Setups. Limit-Ausführungsquote 62 %. Gewinn = Ziel 1 (= 1 R, Abstand wie der Stop) vor dem Stop innerhalb von 60 Handelstagen. Altes Ziel (Swing-Extrem) erreichen nur 21.7 %.

**Basisquote:** 49.6 % aller ausgeführten Setups erreichen Ziel 1 vor dem Stop.

**Modellgüte außerhalb der Trainingszeit** (ab 2025-11-17, 30,895 Signale): AUC 0.547 (0,5 = Zufall), Brier 0.248.
**Schwellen:** Aufnahme in die Top 10 ab 56%, Verbleib bis 52%.

## Trefferquote nach übergeordnetem Trend (EMA 50/200)
Long im Aufwärtstrend bzw. Short im Abwärtstrend = mit dem Trend.

| rt                  |     n |   setups |   trefferquote |   avg_R |
|:--------------------|------:|---------:|---------------:|--------:|
| gegen Trend · long  | 16036 |     2239 |           51.8 |    0.03 |
| gegen Trend · short | 34052 |     4265 |           47.2 |   -0.06 |
| mit Trend · long    | 41930 |     5072 |           54.3 |    0.08 |
| mit Trend · short   | 35719 |     4021 |           46.9 |   -0.07 |
| seitwärts · long    | 15270 |     2781 |           52.6 |    0.05 |
| seitwärts · short   | 19205 |     3109 |           44.4 |   -0.12 |

## Trefferquote nach EMA-Fächer (5>13>20>50>200, in Tradingrichtung, −1 … +1)

| stack        |     n |   setups |   trefferquote |   avg_R |
|:-------------|------:|---------:|---------------:|--------:|
| klar dagegen | 68697 |    10181 |           49.2 |   -0.02 |
| eher dagegen | 49098 |    10174 |           48.6 |   -0.03 |
| eher dafür   | 28552 |     7864 |           49.8 |   -0.01 |
| klar dafür   | 15865 |     4361 |           54   |    0.08 |

## Umkehrkerze am Signaltag

|   trigger |      n |   setups |   trefferquote |   avg_R |
|----------:|-------:|---------:|---------------:|--------:|
|         0 | 149534 |    16285 |           49.5 |   -0.01 |
|         1 |  12678 |     7408 |           50.3 |   -0    |

## Kalibrierung außerhalb der Trainingszeit (vorhergesagt vs. eingetreten)

| p             |     n |   setups |   trefferquote |   avg_R |
|:--------------|------:|---------:|---------------:|--------:|
| (-0.001, 0.4] |    37 |       21 |           45.9 |   -0.11 |
| (0.4, 0.45]   |  3123 |      900 |           43.9 |   -0.14 |
| (0.45, 0.5]   | 12892 |     2021 |           46.4 |   -0.08 |
| (0.5, 0.55]   | 11640 |     1925 |           53.4 |    0.06 |
| (0.55, 0.6]   |  3090 |      785 |           54.8 |    0.1  |
| (0.6, 0.65]   |   113 |       58 |           53.1 |    0.05 |

## Modellgewichte (standardisiert, + = erhöht die Wahrscheinlichkeit)

|                    |   Gewicht |
|:-------------------|----------:|
| is_short           |    -0.154 |
| retrace            |    -0.107 |
| ext_atr            |    -0.065 |
| x20_50_aligned     |    -0.064 |
| bench_aligned      |    -0.054 |
| t1_atr             |    -0.037 |
| x50_200_aligned    |    -0.033 |
| d200_atr           |    -0.027 |
| rs126              |    -0.026 |
| rsi2_side          |    -0.019 |
| conf_ema           |    -0.017 |
| x5_13_turn         |    -0.015 |
| rsi_side           |    -0.015 |
| zone_dist_abs      |    -0.009 |
| atr_pct            |    -0.004 |
| rsi_turn           |    -0.002 |
| trigger            |     0.009 |
| slope200           |     0.027 |
| crv                |     0.034 |
| trend_against      |     0.04  |
| zone_in            |     0.042 |
| trend_aligned      |     0.047 |
| bars_since_extreme |     0.058 |
| stack              |     0.066 |

Hinweis: heutiges Index-Universum (Survivorship Bias), Gebühren und Spreads nicht berücksichtigt.
