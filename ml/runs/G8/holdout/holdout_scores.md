| view | config | verified pairs | detected | clip presence recall | FA/min (neg, 36.37 min) | neg clips w/ class FA | TTFC proxy p50 / p90 s | births/min (pos) | tracks per detected pair | label changes / track-min |
|---|---|---|---|---|---|---|---|---|---|---|
| all12 | G3 | 22 | 11 | 0.5 | 2.859 | 4/16 | 2.24 / 28.11 | 34.63 | 43.18 | 3.873 |
| all12 | G3_bt_pick | 22 | 10 | 0.455 | 1.677 | 4/16 | 7.41 / 37.59 | 24.68 | 35.0 | 3.674 |
| all12 | G3r5 | 22 | 7 | 0.318 | 2.612 | 3/16 | 2.24 / 43.8 | 31.43 | 59.29 | 1.092 |
| all12 | show_s0 | 22 | 7 | 0.318 | 2.474 | 5/16 | 1.28 / 22.94 | 29.63 | 53.14 | 0.695 |
| all12 | show_s1 | 22 | 8 | 0.364 | 2.612 | 4/16 | 7.68 / 56.41 | 32.59 | 42.0 | 1.867 |
| show5 | G3 | 14 | 7 | 0.5 | 2.612 | 3/16 | 2.24 / 43.8 | 31.61 | 59.57 | 1.207 |
| show5 | G3_bt_pick | 14 | 6 | 0.429 | 1.54 | 4/16 | 12.13 / 72.56 | 23.11 | 52.83 | 1.81 |
| show5 | G3r5 | 14 | 7 | 0.5 | 2.612 | 3/16 | 2.24 / 43.8 | 31.43 | 59.29 | 1.092 |
| show5 | show_s0 | 14 | 7 | 0.5 | 2.474 | 5/16 | 1.28 / 22.94 | 29.63 | 53.14 | 0.695 |
| show5 | show_s1 | 14 | 8 | 0.571 | 2.612 | 4/16 | 7.68 / 56.41 | 32.59 | 42.0 | 1.867 |

Per-class clip presence recall (all12 view):

| class | G3 | G3_bt_pick | G3r5 | show_s0 | show_s1 |
|---|---|---|---|---|---|
| apple (n=2) | 1/2 | 1/2 | 1/2 | 1/2 | 1/2 |
| banana (n=4) | 3/4 | 3/4 | 3/4 | 2/4 | 3/4 |
| capsicum (n=1) | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| carrot (n=4) | 1/4 | 0/4 | 1/4 | 1/4 | 1/4 |
| citrus (n=3) | 2/3 | 2/3 | 2/3 | 2/3 | 2/3 |
| cucumber (n=1) | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| lemon_lime (n=2) | 1/2 | 1/2 | 0/2 | 0/2 | 0/2 |
| mango (n=3) | 1/3 | 1/3 | 0/3 | 0/3 | 0/3 |
| potato (n=1) | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 |
| tomato (n=1) | 0/1 | 0/1 | 0/1 | 1/1 | 1/1 |

Uploader-level bootstrap (1000) of candidate - reference:

- G3_bt_pick_vs_G3 (all12): recall diff CI95 [-0.182, 0.0], FA/min diff CI95 [-2.144, -0.669] (25 uploaders)
- show_s0_vs_G3r5 (show5): recall diff CI95 [-0.182, 0.222], FA/min diff CI95 [-1.624, 0.448] (24 uploaders)
- show_s1_vs_G3r5 (show5): recall diff CI95 [0.0, 0.231], FA/min diff CI95 [-1.178, 1.744] (24 uploaders)
- show_s0_vs_G3 (show5, G3 12-class restricted to 5 at display): recall diff CI95 [-0.182, 0.222], FA/min diff CI95 [-1.624, 0.448] (24 uploaders)

Kaggle CPU detector latency (1 thread, ms, median over clips): {"G3": {"p50": 124.3, "p95": 140.8}, "G3r5": {"p50": 123.3, "p95": 139.0}, "show_s0": {"p50": 123.3, "p95": 139.0}, "show_s1": {"p50": 123.2, "p95": 138.6}}
