# Backtest Fibonacci-Setups · 2026-11-19 10:23 UTC

Zeitraum 6y, 623 Titel, 162,205 Signaltage aus 16,470 Setups. Limit-Ausführungsquote 62 %. Gewinn = Ziel 1 vor Stop innerhalb von 60 Handelstagen.

**Basisquote:** 21.7 % aller ausgeführten Setups erreichen Ziel 1 vor dem Stop.

**Modellgüte außerhalb der Trainingszeit** (ab 2025-11-17, 30,896 Signale): AUC 0.605 (0,5 = Zufall), Brier 0.172.
**Schwellen:** Aufnahme in die Top 10 ab 55%, Verbleib bis 47%.

## Trefferquote nach übergeordnetem Trend (EMA 50/200)
Long im Aufwärtstrend bzw. Short im Abwärtstrend = mit dem Trend.

| rt                  |     n |   setups |   trefferquote |   avg_R |
|:--------------------|------:|---------:|---------------:|--------:|
| gegen Trend · long  | 16043 |     2240 |           24.4 |    0.06 |
| gegen Trend · short | 34054 |     4266 |           21.9 |   -0.15 |
| mit Trend · long    | 41924 |     5071 |           25.7 |    0.1  |
| mit Trend · short   | 35714 |     4022 |           18.9 |   -0.17 |
| seitwärts · long    | 15270 |     2782 |           21.2 |    0.15 |
| seitwärts · short   | 19200 |     3107 |           16.1 |   -0.21 |

## Trefferquote nach EMA-Fächer (5>13>20>50>200, in Tradingrichtung, −1 … +1)

| stack        |     n |   setups |   trefferquote |   avg_R |
|:-------------|------:|---------:|---------------:|--------:|
| klar dagegen | 68703 |    10181 |           20.6 |   -0.01 |
| eher dagegen | 49096 |    10174 |           21.4 |   -0.07 |
| eher dafür   | 28547 |     7863 |           22.6 |   -0.1  |
| klar dafür   | 15859 |     4361 |           25.9 |   -0.03 |

## Umkehrkerze am Signaltag

|   trigger |      n |   setups |   trefferquote |   avg_R |
|----------:|-------:|---------:|---------------:|--------:|
|         0 | 149543 |    16287 |           21.6 |   -0.05 |
|         1 |  12662 |     7404 |           22.8 |   -0.02 |

## Kalibrierung außerhalb der Trainingszeit (vorhergesagt vs. eingetreten)

| p             |     n |   setups |   trefferquote |   avg_R |
|:--------------|------:|---------:|---------------:|--------:|
| (-0.001, 0.2] | 11533 |     1554 |           15.8 |   -0.08 |
| (0.2, 0.3]    | 15050 |     2410 |           25.9 |   -0    |
| (0.3, 0.4]    |  4168 |      978 |           30.9 |    0.01 |
| (0.4, 0.5]    |   145 |       69 |           32.4 |   -0.1  |

## Modellgewichte (standardisiert, + = erhöht die Wahrscheinlichkeit)

|                    |   Gewicht |
|:-------------------|----------:|
| t1_atr             |    -0.344 |
| crv                |    -0.195 |
| is_short           |    -0.178 |
| slope200           |    -0.123 |
| rsi_side           |    -0.079 |
| x20_50_aligned     |    -0.039 |
| retrace            |    -0.034 |
| atr_pct            |    -0.018 |
| stack              |    -0.014 |
| conf_ema           |    -0.01  |
| rsi_turn           |    -0.004 |
| x5_13_turn         |    -0.002 |
| zone_dist_abs      |     0.003 |
| bench_aligned      |     0.011 |
| trigger            |     0.013 |
| zone_in            |     0.023 |
| trend_against      |     0.024 |
| trend_aligned      |     0.034 |
| x50_200_aligned    |     0.045 |
| d200_atr           |     0.077 |
| bars_since_extreme |     0.081 |

Hinweis: heutiges Index-Universum (Survivorship Bias), Gebühren und Spreads nicht berücksichtigt.
