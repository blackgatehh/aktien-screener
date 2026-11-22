# Big-Move-Modell · 2026-11-22 09:15 UTC

617 Aktien, 373,632 Aktien-Tage (jeder 2. Tag), Horizont 30 Handelstage, Stop 2 × ATR (5–10 %). Training bis 02.09.2025, Test ab 08.10.2025 (77,834 Aktien-Tage).

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
| long · 10 % | 0.625 | 46.7 % | 47.6 % | 33.8 % | 1.4× |

### long · Kalibrierung (Test, Zehntel nach Vorhersage)

| bin             |   vorhergesagt |   eingetreten |    n |
|:----------------|---------------:|--------------:|-----:|
| (0.0387, 0.157] |          0.129 |         0.188 | 7784 |
| (0.157, 0.193]  |          0.176 |         0.232 | 7783 |
| (0.193, 0.224]  |          0.209 |         0.266 | 7783 |
| (0.224, 0.254]  |          0.239 |         0.287 | 7784 |
| (0.254, 0.284]  |          0.269 |         0.324 | 7783 |
| (0.284, 0.317]  |          0.3   |         0.337 | 7783 |
| (0.317, 0.355]  |          0.336 |         0.359 | 7784 |
| (0.355, 0.403]  |          0.378 |         0.407 | 7783 |
| (0.403, 0.474]  |          0.436 |         0.45  | 7783 |
| (0.474, 0.867]  |          0.546 |         0.527 | 7784 |

### long · typisches Profil der Top 10 (Median)

|                |   Top 10 |   alle |
|:---------------|---------:|-------:|
| atr_pct        |     4.77 |   2.71 |
| ret5           |    -0.21 |   0.1  |
| ret20          |    -0.62 |   0.51 |
| ret60          |    -4.83 |   2.1  |
| ret126         |     0.72 |   5.83 |
| ret252         |    18.61 |   9.99 |
| rs20           |    -1.59 |  -0.54 |
| rs60           |    -8.1  |  -1.57 |
| rs126          |    -8.29 |  -3.49 |
| d_hi252        |   -32.91 | -12.89 |
| d_lo252        |    62.44 |  30.55 |
| stack          |     0    |   0    |
| slope200       |    -0.16 |   0.78 |
| slope50        |    -0.8  |   0.27 |
| d200_atr       |    -0.39 |   1.31 |
| d50_atr        |    -0.36 |   0.22 |
| d20_atr        |    -0.14 |   0.06 |
| x5_13          |     0    |   0    |
| x20_50         |   -19    |   6    |
| x50_200        |    17.5  |  58    |
| rsi            |    48.71 |  50.71 |
| rsi2           |    47.54 |  51.03 |
| vol5_50        |     0.93 |   0.95 |
| vol1_50        |     0.87 |   0.91 |
| gap_up20       |     3.53 |   1.72 |
| gap_dn20       |     3.31 |   1.55 |
| range20_atr    |     4.68 |   4.55 |
| range60_atr    |     9.07 |   7.94 |
| close_pos      |     0.49 |   0.5  |
| updays10       |     5    |   5    |
| bench_side     |     1    |   1    |
| bench_ret20    |     0.85 |   0.8  |
| hi_new20       |     0    |   0    |
| lo_new20       |     0    |   0    |
| dist_ema20_pct |    -0.57 |   0.17 |

| short · 10 % | 0.640 | 43.2 % | 48.1 % | 25.3 % | 1.7× |

### short · Kalibrierung (Test, Zehntel nach Vorhersage)

| bin             |   vorhergesagt |   eingetreten |    n |
|:----------------|---------------:|--------------:|-----:|
| (0.0274, 0.122] |          0.094 |         0.106 | 7784 |
| (0.122, 0.161]  |          0.142 |         0.149 | 7783 |
| (0.161, 0.195]  |          0.178 |         0.193 | 7783 |
| (0.195, 0.228]  |          0.212 |         0.208 | 7784 |
| (0.228, 0.262]  |          0.245 |         0.234 | 7783 |
| (0.262, 0.299]  |          0.28  |         0.253 | 7783 |
| (0.299, 0.342]  |          0.32  |         0.286 | 7784 |
| (0.342, 0.395]  |          0.368 |         0.319 | 7783 |
| (0.395, 0.467]  |          0.429 |         0.355 | 7783 |
| (0.467, 0.763]  |          0.531 |         0.428 | 7784 |

### short · typisches Profil der Top 10 (Median)

|                |   Top 10 |   alle |
|:---------------|---------:|-------:|
| atr_pct        |     4.66 |   2.71 |
| ret5           |    -0.6  |   0.1  |
| ret20          |    -0.91 |   0.51 |
| ret60          |     4.99 |   2.1  |
| ret126         |    15.89 |   5.83 |
| ret252         |    26.01 |   9.99 |
| rs20           |    -1.67 |  -0.54 |
| rs60           |     1.34 |  -1.57 |
| rs126          |     6.32 |  -3.49 |
| d_hi252        |   -20.92 | -12.89 |
| d_lo252        |    62.28 |  30.55 |
| stack          |     0    |   0    |
| slope200       |     1.81 |   0.78 |
| slope50        |     0.69 |   0.27 |
| d200_atr       |     1.32 |   1.31 |
| d50_atr        |     0.09 |   0.22 |
| d20_atr        |    -0.17 |   0.06 |
| x5_13          |     0    |   0    |
| x20_50         |    14    |   6    |
| x50_200        |    93    |  58    |
| rsi            |    49.14 |  50.71 |
| rsi2           |    46.27 |  51.03 |
| vol5_50        |     0.93 |   0.95 |
| vol1_50        |     0.89 |   0.91 |
| gap_up20       |     2.89 |   1.72 |
| gap_dn20       |     2.68 |   1.55 |
| range20_atr    |     4.47 |   4.55 |
| range60_atr    |     7.67 |   7.94 |
| close_pos      |     0.48 |   0.5  |
| updays10       |     5    |   5    |
| bench_side     |     1    |   1    |
| bench_ret20    |     0.72 |   0.8  |
| hi_new20       |     0    |   0    |
| lo_new20       |     0    |   0    |
| dist_ema20_pct |    -0.68 |   0.17 |

## Weitere Ziele mit demselben Ranking (Test, Top 10 je Tag)

| | Top 10 | Basis |
|---|---|---|
| long +15 % | 32.4 % | 19.3 % |
| long +20 % | 22.7 % | 10.8 % |
| short −15 % | 27.1 % | 12.2 % |
| short −20 % | 16.1 % | 5.6 % |

## Richtung: Ranking-Varianten (Test)

| Ranking | Top k | Ziel ±10 % zuerst | Gegenrichtung zuerst | Ø Ergebnis je Trade |
|---|---|---|---|---|
| Long nach p(+10) − p(−10) | 3 | 38.2 % | 28.3 % | +0.90 % |
| Long nach p(+10) − p(−10) | 10 | 37.5 % | 27.4 % | +0.96 % |
| Short nach p(−10) − p(+10) | 3 | 38.5 % | 32.8 % | +0.84 % |
| Short nach p(−10) − p(+10) | 10 | 35.5 % | 34.2 % | +0.32 % |
| long nach geschätztem Ergebnis | 3 | 40.8 % | 27.0 % | +1.27 % |
| long nach geschätztem Ergebnis | 10 | 37.8 % | 26.7 % | +1.06 % |
| short nach geschätztem Ergebnis | 3 | 40.9 % | 35.6 % | +0.51 % |
| short nach geschätztem Ergebnis | 10 | 37.6 % | 34.8 % | +0.33 % |

## Ergebnis pro Trade (Test): Ausstieg bei ±10 %-Ziel, Stop oder nach 30 Tagen

| | Ø Ergebnis Top 3 | Ø Ergebnis Top 10 | Ø alle | Ø Stop | Gegenrichtung −10 % zuerst (Top 10) |
|---|---|---|---|---|---|
| long | +0.49 % | +0.66 % | +0.72 % | 8.7 % | 39.6 % |
| short | +0.44 % | +0.05 % | -0.63 % | 8.6 % | 43.1 % |

Hinweis: heutiges Index-Universum (Survivorship Bias), keine Kosten. Ziel und Stop am selben Tag zählen als Stop.
