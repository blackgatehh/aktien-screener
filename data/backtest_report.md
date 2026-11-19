# Backtest Fibonacci-Setups · 2026-11-19 10:35 UTC

Zeitraum 6y, 623 Titel, 162,212 Signaltage aus 16,468 Setups. Limit-Ausführungsquote 62 %. Gewinn = Ziel 1 vor Stop innerhalb von 60 Handelstagen.

**Basisquote:** 21.7 % aller ausgeführten Setups erreichen Ziel 1 vor dem Stop.

**Modellgüte außerhalb der Trainingszeit** (ab 2025-11-17, 30,895 Signale): AUC 0.605 (0,5 = Zufall), Brier 0.172.
**Schwellen:** Aufnahme in die Top 10 ab 55%, Verbleib bis 47%.

## Trefferquote nach übergeordnetem Trend (EMA 50/200)
Long im Aufwärtstrend bzw. Short im Abwärtstrend = mit dem Trend.

| rt                  |     n |   setups |   trefferquote |   avg_R |
|:--------------------|------:|---------:|---------------:|--------:|
| gegen Trend · long  | 16036 |     2239 |           24.4 |    0.06 |
| gegen Trend · short | 34052 |     4265 |           21.9 |   -0.15 |
| mit Trend · long    | 41930 |     5072 |           25.8 |    0.1  |
| mit Trend · short   | 35719 |     4021 |           19   |   -0.17 |
| seitwärts · long    | 15270 |     2781 |           21.2 |    0.15 |
| seitwärts · short   | 19205 |     3109 |           16.1 |   -0.21 |

## Trefferquote nach EMA-Fächer (5>13>20>50>200, in Tradingrichtung, −1 … +1)

| stack        |     n |   setups |   trefferquote |   avg_R |
|:-------------|------:|---------:|---------------:|--------:|
| klar dagegen | 68697 |    10181 |           20.7 |   -0.01 |
| eher dagegen | 49098 |    10174 |           21.4 |   -0.07 |
| eher dafür   | 28552 |     7864 |           22.7 |   -0.1  |
| klar dafür   | 15865 |     4361 |           26   |   -0.03 |

## Umkehrkerze am Signaltag

|   trigger |      n |   setups |   trefferquote |   avg_R |
|----------:|-------:|---------:|---------------:|--------:|
|         0 | 149534 |    16285 |           21.7 |   -0.05 |
|         1 |  12678 |     7408 |           22.8 |   -0.02 |

## Kalibrierung außerhalb der Trainingszeit (vorhergesagt vs. eingetreten)

| p             |     n |   setups |   trefferquote |   avg_R |
|:--------------|------:|---------:|---------------:|--------:|
| (-0.001, 0.2] | 11471 |     1556 |           15.7 |   -0.09 |
| (0.2, 0.3]    | 14985 |     2412 |           25.8 |    0    |
| (0.3, 0.4]    |  4277 |     1024 |           31.1 |    0.01 |
| (0.4, 0.5]    |   162 |       77 |           30.9 |   -0.14 |

## Modellgewichte (standardisiert, + = erhöht die Wahrscheinlichkeit)

|                    |   Gewicht |
|:-------------------|----------:|
| t1_atr             |    -0.334 |
| crv                |    -0.194 |
| is_short           |    -0.181 |
| slope200           |    -0.137 |
| rsi_side           |    -0.053 |
| retrace            |    -0.041 |
| ext_atr            |    -0.038 |
| stack              |    -0.034 |
| x20_50_aligned     |    -0.031 |
| rsi2_side          |    -0.025 |
| atr_pct            |    -0.017 |
| conf_ema           |    -0.014 |
| zone_dist_abs      |    -0.003 |
| x5_13_turn         |    -0.001 |
| rsi_turn           |    -0     |
| trigger            |     0.014 |
| bench_aligned      |     0.022 |
| zone_in            |     0.025 |
| rs126              |     0.026 |
| trend_against      |     0.029 |
| trend_aligned      |     0.038 |
| d200_atr           |     0.046 |
| x50_200_aligned    |     0.047 |
| bars_since_extreme |     0.077 |

Hinweis: heutiges Index-Universum (Survivorship Bias), Gebühren und Spreads nicht berücksichtigt.
