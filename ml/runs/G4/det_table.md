| model | imgsz | test (n=557) mAP50 / 50-95 | test_rf (n=149) mAP50 / 50-95 | test_oiv7 (n=123) mAP50 / 50-95 | test_oiv7c (n=181) mAP50 / 50-95 | pooled (n=829) mAP50 / 50-95 | neg_test FA img rate (n=80, conf 0.35) |
|---|---|---|---|---|---|---|---|
| G1champ (yolo26n 320; raw-head eval as in G1-G3 docs) | 320 | 0.125 / 0.065 | 0.323 / 0.177 | 0.112 / 0.082 | - | 0.095 / 0.049 | - |
| G3champ control (yolo11n 640->480) | 480 | 0.224 / 0.139 | 0.355 / 0.231 | 0.381 / 0.282 | 0.634 / 0.448 | 0.314 / 0.218 | 0.025 |
| A1 hygiene off [A1hyg] yolo11n 640->480 | 480 | 0.323 / 0.200 | 0.406 / 0.266 | 0.379 / 0.285 | 0.665 / 0.515 | 0.385 / 0.260 | 0.0 |
| A2 backgrounds 15% [A2bg15] yolo11n 640->480 | 480 | 0.215 / 0.137 | 0.374 / 0.256 | 0.454 / 0.377 | 0.517 / 0.396 | 0.297 / 0.207 | 0.0125 |

Per-class mAP50 on test_rf:

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G1champ (yolo26n 320; raw-head eval as in G1-G3 docs) | 0.74 | 0.28 | - | 0.82 | - | - | 0.02 | 0.33 | - | 0.05 | 0.25 | 0.09 |
| G3champ control (yolo11n 640->480) | 0.84 | 0.27 | - | 0.67 | - | - | 0.02 | 0.68 | - | 0.05 | 0.30 | 0.02 |
| A1 hygiene off [A1hyg] yolo11n 640->480 | 0.81 | 0.44 | - | 0.83 | - | - | 0.01 | 0.57 | - | 0.10 | 0.37 | 0.12 |
| A2 backgrounds 15% [A2bg15] yolo11n 640->480 | 0.84 | 0.27 | - | 0.81 | - | - | 0.01 | 0.58 | - | 0.08 | 0.38 | 0.01 |

Per-class mAP50 on pooled:

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G1champ (yolo26n 320; raw-head eval as in G1-G3 docs) | 0.12 | 0.09 | 0.00 | 0.26 | - | 0.00 | 0.04 | 0.23 | 0.06 | 0.03 | 0.19 | 0.02 |
| G3champ control (yolo11n 640->480) | 0.34 | 0.25 | 0.36 | 0.45 | - | 0.72 | 0.02 | 0.39 | 0.14 | 0.24 | 0.31 | 0.22 |
| A1 hygiene off [A1hyg] yolo11n 640->480 | 0.41 | 0.37 | 0.32 | 0.57 | - | 0.71 | 0.23 | 0.41 | 0.22 | 0.30 | 0.39 | 0.32 |
| A2 backgrounds 15% [A2bg15] yolo11n 640->480 | 0.33 | 0.21 | 0.17 | 0.42 | - | 0.79 | 0.04 | 0.35 | 0.10 | 0.32 | 0.33 | 0.19 |

Per-class mAP50 on test_oiv7c:

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3champ control (yolo11n 640->480) | - | 0.53 | - | 0.45 | - | - | 0.46 | 0.74 | - | - | 0.99 | - |
| A1 hygiene off [A1hyg] yolo11n 640->480 | - | 0.49 | - | 0.45 | - | - | 0.49 | 0.94 | - | - | 0.94 | - |
| A2 backgrounds 15% [A2bg15] yolo11n 640->480 | - | 0.28 | - | 0.45 | - | - | 0.49 | 0.37 | - | - | 0.99 | - |

test_rf per-class regressions > 1 pt (strict rule), vs G1 champion | vs G3 control:

- G1champ (yolo26n 320; raw-head eval as in G1-G3 docs): vs G1 none | vs G3 {'banana': -0.0914, 'tomato': -0.3447, 'carrot': -0.0567}
- G3champ control (yolo11n 640->480): vs G1 {'apple': -0.0131, 'citrus': -0.1553, 'capsicum': -0.0763} | vs G3 none
- A1 hygiene off [A1hyg] yolo11n 640->480: vs G1 none | vs G3 {'banana': -0.0216, 'lemon_lime': -0.0164, 'tomato': -0.1015}
- A2 backgrounds 15% [A2bg15] yolo11n 640->480: vs G1 {'citrus': -0.0124, 'capsicum': -0.0849} | vs G3 {'lemon_lime': -0.0159, 'tomato': -0.0938}
