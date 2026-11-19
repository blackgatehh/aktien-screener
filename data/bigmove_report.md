# Big-Move-Modell · 2026-11-19 11:51 UTC

617 Aktien, 374,162 Aktien-Tage (jeder 2. Tag), Horizont 30 Handelstage, Stop 2 × ATR (5–10 %). Training bis 01.09.2025, Test ab 07.10.2025 (77,877 Aktien-Tage).

## Basisquoten (alle Aktien-Tage)

| Ziel vor Stop | Long | Short |
|---|---|---|
| 10 % | 29.9 % | 24.1 % |
| 15 % | 15.7 % | 11.6 % |
| 20 % | 8.3 % | 5.4 % |

## Modell außerhalb der Trainingszeit

Top 10 = die 10 Aktien mit der höchsten vorhergesagten Wahrscheinlichkeit je Tag.

| Richtung · Ziel | AUC | Top 10 je Tag | Top 3 je Tag | Basis | Faktor |
|---|---|---|---|---|---|
| long · 10 % | 0.625 | 46.2 % | 44.3 % | 33.6 % | 1.4× |

### long · Kalibrierung (Test, Zehntel nach Vorhersage)

| bin             |   vorhergesagt |   eingetreten |    n |
|:----------------|---------------:|--------------:|-----:|
| (0.0473, 0.158] |          0.131 |         0.192 | 7788 |
| (0.158, 0.193]  |          0.176 |         0.23  | 7788 |
| (0.193, 0.223]  |          0.208 |         0.259 | 7787 |
| (0.223, 0.252]  |          0.238 |         0.295 | 7788 |
| (0.252, 0.282]  |          0.267 |         0.306 | 7788 |
| (0.282, 0.314]  |          0.298 |         0.33  | 7787 |
| (0.314, 0.352]  |          0.333 |         0.366 | 7788 |
| (0.352, 0.401]  |          0.375 |         0.407 | 7787 |
| (0.401, 0.47]   |          0.433 |         0.446 | 7788 |
| (0.47, 0.91]    |          0.542 |         0.528 | 7788 |

### long · typisches Profil der Top 10 (Median)

|                |   Top 10 |   alle |
|:---------------|---------:|-------:|
| atr_pct        |     4.75 |   2.71 |
| ret5           |    -0.34 |   0.08 |
| ret20          |    -1.18 |   0.55 |
| ret60          |    -6.28 |   2.14 |
| ret126         |     2.24 |   5.99 |
| ret252         |    25.21 |  10.02 |
| rs20           |    -1.71 |  -0.53 |
| rs60           |    -9.21 |  -1.56 |
| rs126          |    -5.79 |  -3.46 |
| d_hi252        |   -32.54 | -12.82 |
| d_lo252        |    69.65 |  30.63 |
| stack          |     0    |   0    |
| slope200       |     0.03 |   0.79 |
| slope50        |    -1.1  |   0.29 |
| d200_atr       |    -0.21 |   1.32 |
| d50_atr        |    -0.53 |   0.23 |
| d20_atr        |    -0.16 |   0.07 |
| x5_13          |    -1    |   0    |
| x20_50         |   -21    |   6    |
| x50_200        |    28    |  59    |
| rsi            |    48.16 |  50.76 |
| rsi2           |    46.73 |  50.7  |
| vol5_50        |     0.94 |   0.95 |
| vol1_50        |     0.88 |   0.91 |
| gap_up20       |     3.53 |   1.71 |
| gap_dn20       |     3.37 |   1.55 |
| range20_atr    |     4.68 |   4.55 |
| range60_atr    |     9.18 |   7.94 |
| close_pos      |     0.5  |   0.49 |
| updays10       |     5    |   5    |
| bench_side     |     1    |   1    |
| bench_ret20    |     0.87 |   0.8  |
| hi_new20       |     0    |   0    |
| lo_new20       |     0    |   0    |
| dist_ema20_pct |    -0.66 |   0.18 |

| short · 10 % | 0.633 | 40.1 % | 43.5 % | 25.4 % | 1.6× |

### short · Kalibrierung (Test, Zehntel nach Vorhersage)

| bin             |   vorhergesagt |   eingetreten |    n |
|:----------------|---------------:|--------------:|-----:|
| (0.0223, 0.121] |          0.093 |         0.108 | 7788 |
| (0.121, 0.159]  |          0.141 |         0.167 | 7788 |
| (0.159, 0.193]  |          0.176 |         0.19  | 7787 |
| (0.193, 0.227]  |          0.21  |         0.21  | 7788 |
| (0.227, 0.262]  |          0.244 |         0.235 | 7788 |
| (0.262, 0.3]    |          0.281 |         0.267 | 7787 |
| (0.3, 0.345]    |          0.322 |         0.28  | 7788 |
| (0.345, 0.401]  |          0.372 |         0.313 | 7787 |
| (0.401, 0.475]  |          0.436 |         0.351 | 7788 |
| (0.475, 0.838]  |          0.539 |         0.421 | 7788 |

### short · typisches Profil der Top 10 (Median)

|                |   Top 10 |   alle |
|:---------------|---------:|-------:|
| atr_pct        |     4.68 |   2.71 |
| ret5           |    -0.7  |   0.08 |
| ret20          |    -0.68 |   0.55 |
| ret60          |     3.36 |   2.14 |
| ret126         |    17.63 |   5.99 |
| ret252         |    28.67 |  10.02 |
| rs20           |    -1.5  |  -0.53 |
| rs60           |    -0.42 |  -1.56 |
| rs126          |     9.54 |  -3.46 |
| d_hi252        |   -19.89 | -12.82 |
| d_lo252        |    63.35 |  30.63 |
| stack          |     0    |   0    |
| slope200       |     2.13 |   0.79 |
| slope50        |     0.65 |   0.29 |
| d200_atr       |     1.54 |   1.32 |
| d50_atr        |     0.1  |   0.23 |
| d20_atr        |    -0.16 |   0.07 |
| x5_13          |     0    |   0    |
| x20_50         |    13    |   6    |
| x50_200        |   108    |  59    |
| rsi            |    49.06 |  50.76 |
| rsi2           |    45.29 |  50.7  |
| vol5_50        |     0.93 |   0.95 |
| vol1_50        |     0.88 |   0.91 |
| gap_up20       |     2.91 |   1.71 |
| gap_dn20       |     2.7  |   1.55 |
| range20_atr    |     4.45 |   4.55 |
| range60_atr    |     7.68 |   7.94 |
| close_pos      |     0.48 |   0.49 |
| updays10       |     5    |   5    |
| bench_side     |     1    |   1    |
| bench_ret20    |     0.74 |   0.8  |
| hi_new20       |     0    |   0    |
| lo_new20       |     0    |   0    |
| dist_ema20_pct |    -0.64 |   0.18 |

## Weitere Ziele mit demselben Ranking (Test, Top 10 je Tag)

| | Top 10 | Basis |
|---|---|---|
| long +15 % | 31.0 % | 19.1 % |
| long +20 % | 22.0 % | 10.7 % |
| short −15 % | 23.7 % | 12.2 % |
| short −20 % | 13.9 % | 5.6 % |

## Ergebnis pro Trade (Test): Ausstieg bei ±10 %-Ziel, Stop oder nach 30 Tagen

| | Ø Ergebnis Top 3 | Ø Ergebnis Top 10 | Ø alle | Ø Stop | Gegenrichtung −10 % zuerst (Top 10) |
|---|---|---|---|---|---|
| long | -0.08 % | +0.61 % | +0.69 % | 8.7 % | 39.4 % |
| short | -0.36 % | -0.52 % | -0.60 % | 8.6 % | 46.4 % |

Hinweis: heutiges Index-Universum (Survivorship Bias), keine Kosten. Ziel und Stop am selben Tag zählen als Stop.
