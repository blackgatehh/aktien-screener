# Big-Move-Modell · 2026-11-19 11:55 UTC

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
| long · 10 % | 0.625 | 46.9 % | 49.0 % | 33.6 % | 1.4× |

### long · Kalibrierung (Test, Zehntel nach Vorhersage)

| bin                          |   vorhergesagt |   eingetreten |    n |
|:-----------------------------|---------------:|--------------:|-----:|
| (0.054599999999999996, 0.16] |          0.132 |         0.192 | 7788 |
| (0.16, 0.195]                |          0.178 |         0.229 | 7788 |
| (0.195, 0.225]               |          0.21  |         0.267 | 7787 |
| (0.225, 0.254]               |          0.24  |         0.284 | 7788 |
| (0.254, 0.284]               |          0.269 |         0.309 | 7788 |
| (0.284, 0.317]               |          0.3   |         0.334 | 7787 |
| (0.317, 0.355]               |          0.335 |         0.361 | 7788 |
| (0.355, 0.404]               |          0.378 |         0.411 | 7787 |
| (0.404, 0.475]               |          0.437 |         0.442 | 7788 |
| (0.475, 0.873]               |          0.546 |         0.53  | 7788 |

### long · typisches Profil der Top 10 (Median)

|                |   Top 10 |   alle |
|:---------------|---------:|-------:|
| atr_pct        |     4.74 |   2.71 |
| ret5           |    -0.48 |   0.08 |
| ret20          |    -0.91 |   0.55 |
| ret60          |    -5.59 |   2.14 |
| ret126         |     4.38 |   5.99 |
| ret252         |    26.3  |  10.02 |
| rs20           |    -1.69 |  -0.53 |
| rs60           |    -8.78 |  -1.56 |
| rs126          |    -5.09 |  -3.46 |
| d_hi252        |   -31.82 | -12.82 |
| d_lo252        |    73.15 |  30.63 |
| stack          |     0    |   0    |
| slope200       |     0.21 |   0.79 |
| slope50        |    -0.89 |   0.29 |
| d200_atr       |    -0    |   1.32 |
| d50_atr        |    -0.46 |   0.23 |
| d20_atr        |    -0.16 |   0.07 |
| x5_13          |    -1    |   0    |
| x20_50         |   -18    |   6    |
| x50_200        |    33    |  59    |
| rsi            |    48.3  |  50.76 |
| rsi2           |    45.29 |  50.7  |
| vol5_50        |     0.94 |   0.95 |
| vol1_50        |     0.87 |   0.91 |
| gap_up20       |     3.6  |   1.71 |
| gap_dn20       |     3.31 |   1.55 |
| range20_atr    |     4.65 |   4.55 |
| range60_atr    |     9.19 |   7.94 |
| close_pos      |     0.5  |   0.49 |
| updays10       |     5    |   5    |
| bench_side     |     1    |   1    |
| bench_ret20    |     0.9  |   0.8  |
| hi_new20       |     0    |   0    |
| lo_new20       |     0    |   0    |
| dist_ema20_pct |    -0.66 |   0.18 |

| short · 10 % | 0.637 | 42.1 % | 45.4 % | 25.4 % | 1.7× |

### short · Kalibrierung (Test, Zehntel nach Vorhersage)

| bin                          |   vorhergesagt |   eingetreten |    n |
|:-----------------------------|---------------:|--------------:|-----:|
| (0.024999999999999998, 0.12] |          0.093 |         0.109 | 7788 |
| (0.12, 0.159]                |          0.14  |         0.161 | 7788 |
| (0.159, 0.192]               |          0.176 |         0.189 | 7787 |
| (0.192, 0.226]               |          0.209 |         0.211 | 7788 |
| (0.226, 0.262]               |          0.244 |         0.233 | 7788 |
| (0.262, 0.3]                 |          0.28  |         0.255 | 7787 |
| (0.3, 0.345]                 |          0.322 |         0.282 | 7788 |
| (0.345, 0.401]               |          0.372 |         0.317 | 7787 |
| (0.401, 0.477]               |          0.437 |         0.365 | 7788 |
| (0.477, 0.795]               |          0.539 |         0.42  | 7788 |

### short · typisches Profil der Top 10 (Median)

|                |   Top 10 |   alle |
|:---------------|---------:|-------:|
| atr_pct        |     4.72 |   2.71 |
| ret5           |    -0.67 |   0.08 |
| ret20          |    -0.59 |   0.55 |
| ret60          |     2.82 |   2.14 |
| ret126         |    15.59 |   5.99 |
| ret252         |    28.08 |  10.02 |
| rs20           |    -1.44 |  -0.53 |
| rs60           |    -0.42 |  -1.56 |
| rs126          |     7.6  |  -3.46 |
| d_hi252        |   -20.7  | -12.82 |
| d_lo252        |    61.24 |  30.63 |
| stack          |     0    |   0    |
| slope200       |     1.86 |   0.79 |
| slope50        |     0.42 |   0.29 |
| d200_atr       |     1.29 |   1.32 |
| d50_atr        |     0.01 |   0.23 |
| d20_atr        |    -0.15 |   0.07 |
| x5_13          |     0    |   0    |
| x20_50         |     9    |   6    |
| x50_200        |   107    |  59    |
| rsi            |    49.02 |  50.76 |
| rsi2           |    44.42 |  50.7  |
| vol5_50        |     0.93 |   0.95 |
| vol1_50        |     0.87 |   0.91 |
| gap_up20       |     2.98 |   1.71 |
| gap_dn20       |     2.68 |   1.55 |
| range20_atr    |     4.42 |   4.55 |
| range60_atr    |     7.66 |   7.94 |
| close_pos      |     0.48 |   0.49 |
| updays10       |     5    |   5    |
| bench_side     |     1    |   1    |
| bench_ret20    |     0.73 |   0.8  |
| hi_new20       |     0    |   0    |
| lo_new20       |     0    |   0    |
| dist_ema20_pct |    -0.66 |   0.18 |

## Weitere Ziele mit demselben Ranking (Test, Top 10 je Tag)

| | Top 10 | Basis |
|---|---|---|
| long +15 % | 31.5 % | 19.1 % |
| long +20 % | 22.8 % | 10.7 % |
| short −15 % | 26.0 % | 12.2 % |
| short −20 % | 15.3 % | 5.6 % |

## Richtung: Ranking-Varianten (Test)

| Ranking | Top k | Ziel ±10 % zuerst | Gegenrichtung zuerst | Ø Ergebnis je Trade |
|---|---|---|---|---|
| Long nach p(+10) − p(−10) | 3 | 37.1 % | 29.3 % | +0.81 % |
| Long nach p(+10) − p(−10) | 10 | 37.7 % | 28.6 % | +0.98 % |
| Short nach p(−10) − p(+10) | 3 | 31.7 % | 38.4 % | -0.65 % |
| Short nach p(−10) − p(+10) | 10 | 31.7 % | 35.1 % | -0.32 % |
| long nach geschätztem Ergebnis | 3 | 38.6 % | 30.5 % | +1.04 % |
| long nach geschätztem Ergebnis | 10 | 37.2 % | 29.0 % | +1.00 % |
| short nach geschätztem Ergebnis | 3 | 38.4 % | 35.8 % | +0.40 % |
| short nach geschätztem Ergebnis | 10 | 34.2 % | 36.0 % | -0.08 % |

## Ergebnis pro Trade (Test): Ausstieg bei ±10 %-Ziel, Stop oder nach 30 Tagen

| | Ø Ergebnis Top 3 | Ø Ergebnis Top 10 | Ø alle | Ø Stop | Gegenrichtung −10 % zuerst (Top 10) |
|---|---|---|---|---|---|
| long | +0.80 % | +0.71 % | +0.69 % | 8.7 % | 38.9 % |
| short | -0.13 % | -0.20 % | -0.60 % | 8.7 % | 44.9 % |

Hinweis: heutiges Index-Universum (Survivorship Bias), keine Kosten. Ziel und Stop am selben Tag zählen als Stop.
