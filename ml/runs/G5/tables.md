Device: sandbox CPU (2-core aarch64), PyTorch .pt eval, conf 0.001, iou 0.7. `test_rf_nostrips` is a G5 VIEW (test_rf with the 110 sliced capsicum-strip boxes removed); the locked test_rf is unchanged.

| model | imgsz | test (n=557) mAP50 / 50-95 | test_rf (n=149) mAP50 / 50-95 | test_oiv7 (n=123) mAP50 / 50-95 | test_oiv7c (n=181) mAP50 / 50-95 | pooled (n=829) mAP50 / 50-95 | test_rf_nostrips (n=149) mAP50 / 50-95 | neg_test img FA (n=80, conf 0.35) |
|---|---|---|---|---|---|---|---|---|
| G1 champion yolo26n (raw-head eval) | 320 | 0.125 / 0.065 | 0.323 / 0.177 | 0.112 / 0.082 | - | 0.095 / 0.049 | - | - |
| G3 control yolo11n (CHAMPION) | 480 | 0.224 / 0.139 | 0.355 / 0.231 | 0.381 / 0.282 | 0.634 / 0.448 | 0.314 / 0.218 | 0.404 / 0.263 | 0.025 |
| A1 hygiene off (G4) | 480 | 0.323 / 0.200 | 0.406 / 0.266 | 0.379 / 0.285 | 0.665 / 0.515 | 0.385 / 0.260 | 0.448 / 0.296 | 0.0 |
| G5 ft0 = A1 fine-tune @480 (1500-img subset, Kaggle CPU) [ft0] | 480 | 0.288 / 0.177 | 0.384 / 0.249 | 0.414 / 0.298 | 0.629 / 0.482 | 0.348 / 0.230 | 0.433 / 0.282 | 0.0125 |
| G5 fthn = ft0 recipe + video hard negatives [fthn] | 480 | - | - | - | - | 0.331 / 0.221 | 0.378 / 0.248 | 0.0375 |
| G5 fthnc = fthn + guava + whole capsicum [fthnc] | 480 | 0.275 / 0.168 | 0.393 / 0.258 | 0.522 / 0.390 | 0.496 / 0.367 | 0.360 / 0.240 | 0.439 / 0.289 | 0.0 |

New external splits (Kaggle T4 eval inside the training kernel, imgsz 480; not CPU):

| model | test_guava mAP50 (n) | test_capsicum_whole mAP50 (n) |
|---|---|---|
| G5 fthnc = fthn + guava + whole capsicum [fthnc] | 0.9294 (121) | 0.7013 (12) |

Per-class mAP50, test_rf:

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum | shared-class mean | new-class (guava) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G1 champion yolo26n (raw-head eval) | 0.74 | 0.28 | - | 0.82 | - | - | 0.02 | 0.33 | - | 0.05 | 0.25 | 0.09 | 0.323 | no GT |
| G3 control yolo11n (CHAMPION) | 0.84 | 0.27 | - | 0.67 | - | - | 0.02 | 0.68 | - | 0.05 | 0.30 | 0.02 | 0.355 | no GT |
| A1 hygiene off (G4) | 0.81 | 0.44 | - | 0.83 | - | - | 0.01 | 0.57 | - | 0.10 | 0.37 | 0.12 | 0.406 | no GT |
| G5 ft0 = A1 fine-tune @480 (1500-img subset, Kaggle CPU) [ft0] | 0.77 | 0.41 | - | 0.83 | - | - | 0.01 | 0.54 | - | 0.13 | 0.34 | 0.04 | 0.384 | no GT |
| G5 fthnc = fthn + guava + whole capsicum [fthnc] | 0.80 | 0.45 | - | 0.68 | - | - | 0.02 | 0.59 | - | 0.10 | 0.44 | 0.08 | 0.393 | no GT |

Per-class mAP50, pooled:

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum | shared-class mean | new-class (guava) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G1 champion yolo26n (raw-head eval) | 0.12 | 0.09 | 0.00 | 0.26 | - | 0.00 | 0.04 | 0.23 | 0.06 | 0.03 | 0.19 | 0.02 | 0.095 | no GT |
| G3 control yolo11n (CHAMPION) | 0.34 | 0.25 | 0.36 | 0.45 | - | 0.72 | 0.02 | 0.39 | 0.14 | 0.24 | 0.31 | 0.22 | 0.314 | no GT |
| A1 hygiene off (G4) | 0.41 | 0.37 | 0.32 | 0.57 | - | 0.71 | 0.23 | 0.41 | 0.22 | 0.30 | 0.39 | 0.32 | 0.385 | no GT |
| G5 ft0 = A1 fine-tune @480 (1500-img subset, Kaggle CPU) [ft0] | 0.39 | 0.32 | 0.31 | 0.55 | - | 0.68 | 0.16 | 0.38 | 0.12 | 0.30 | 0.36 | 0.26 | 0.348 | no GT |
| G5 fthn = ft0 recipe + video hard negatives [fthn] | 0.39 | 0.30 | 0.24 | 0.52 | - | 0.68 | 0.15 | 0.35 | 0.07 | 0.31 | 0.36 | 0.26 | 0.331 | no GT |
| G5 fthnc = fthn + guava + whole capsicum [fthnc] | 0.41 | 0.30 | 0.36 | 0.55 | - | 0.78 | 0.16 | 0.38 | 0.08 | 0.30 | 0.36 | 0.28 | 0.360 | no GT |

Per-class mAP50, test_oiv7c:

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum | shared-class mean | new-class (guava) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3 control yolo11n (CHAMPION) | - | 0.53 | - | 0.45 | - | - | 0.46 | 0.74 | - | - | 0.99 | - | 0.634 | no GT |
| A1 hygiene off (G4) | - | 0.49 | - | 0.45 | - | - | 0.49 | 0.94 | - | - | 0.94 | - | 0.665 | no GT |
| G5 ft0 = A1 fine-tune @480 (1500-img subset, Kaggle CPU) [ft0] | - | 0.34 | - | 0.41 | - | - | 0.48 | 0.99 | - | - | 0.91 | - | 0.629 | no GT |
| G5 fthnc = fthn + guava + whole capsicum [fthnc] | - | 0.59 | - | 0.38 | - | - | 0.43 | 0.17 | - | - | 0.91 | - | 0.496 | no GT |

Strict rule: test_rf per-class drops > 1 pt vs G1 champion | vs G3 control:

- G1 champion yolo26n (raw-head eval): vs G1 none | vs G3 {'banana': -0.0914, 'tomato': -0.3447, 'carrot': -0.0567}
- G3 control yolo11n (CHAMPION): vs G1 {'apple': -0.0131, 'citrus': -0.1553, 'capsicum': -0.0763} | vs G3 none
- A1 hygiene off (G4): vs G1 none | vs G3 {'banana': -0.0216, 'lemon_lime': -0.0164, 'tomato': -0.1015}
- G5 ft0 = A1 fine-tune @480 (1500-img subset, Kaggle CPU) [ft0]: vs G1 {'capsicum': -0.0505} | vs G3 {'banana': -0.0626, 'tomato': -0.1379}
- G5 fthnc = fthn + guava + whole capsicum [fthnc]: vs G1 {'citrus': -0.1413, 'capsicum': -0.0173} | vs G3 {'banana': -0.0338, 'tomato': -0.0864}

Fixed-frame TEST gauntlet (stride 1; G1 det/quality/neg clips + G2 negtest clip; sandbox CPU; det imgsz 480; cls G3 E224 T=0.25; guard rule 2 off). G3champ_msc0 / A1hyg rows are the G4 runs (same code path, temporal off).

| run | temporal | det_seg | det_frame | flick_static | flick_all | ttfc_p90 | q_acc | rot_rec | grade_flick | fa_g1neg | ep_g1neg | fa_negtest | ep_negtest | det_p50 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3champ_msc0_r1 | None | 0.667 | 0.496 | 0.000 | 1.791 | 760.000 | 0.929 | 0.875 | 0.000 | 1.250 | 1.250 | 0.000 | 0.000 | 46.276 |
| G3champ_msc0_r2 | None | 0.667 | 0.496 | 0.000 | 1.791 | 760.000 | 0.929 | 0.875 | 0.000 | 1.250 | 1.250 | 0.000 | 0.000 | 46.402 |
| A1hyg_r1 | None | 0.458 | 0.398 | 4.792 | 4.108 | 2000.000 | 0.923 | 0.750 | 0.625 | 6.250 | 3.750 | 1.500 | 1.120 | 45.728 |
| A1hyg_r2 | None | 0.458 | 0.398 | 4.792 | 4.108 | 2000.000 | 0.923 | 0.750 | 0.625 | 6.250 | 3.750 | 1.500 | 1.120 | 45.169 |
| A1hyg_tw5_r1 | {"window": 5, "iouLink": 0.5, "preScore": 0.2, "minScore": 0.35} | 0.500 | 0.359 | 2.917 | 2.001 | 933.333 | 0.923 | 0.750 | 0.312 | 5.000 | 1.250 | 1.120 | 0.750 | 51.741 |
| A1hyg_tw5_r2 | {"window": 5, "iouLink": 0.5, "preScore": 0.2, "minScore": 0.35} | 0.500 | 0.359 | 2.917 | 2.001 | 933.333 | 0.923 | 0.750 | 0.312 | 5.000 | 1.250 | 1.120 | 0.750 | 45.585 |
| G3champ_tw3_r1 | {"window": 3, "iouLink": 0.5, "preScore": 0.2, "minScore": 0.35} | 0.625 | 0.500 | 0.417 | 0.421 | 800.000 | 0.929 | 0.875 | 0.000 | 1.250 | 1.250 | 0.000 | 0.000 | 55.773 |
| G3champ_tw3_r2 | {"window": 3, "iouLink": 0.5, "preScore": 0.2, "minScore": 0.35} | 0.625 | 0.500 | 0.417 | 0.421 | 800.000 | 0.929 | 0.875 | 0.000 | 1.250 | 1.250 | 0.000 | 0.000 | 48.447 |
| ft0_r1 | None | 0.542 | 0.438 | 0.000 | 0.632 | 2373.333 | 0.923 | 0.750 | 0.625 | 17.500 | 5.000 | 1.120 | 0.750 | 49.048 |
| fthn_r1 | None | 0.542 | 0.411 | 4.375 | 3.160 | 1160.000 | 0.923 | 0.750 | 0.625 | 8.750 | 5.000 | 2.620 | 1.880 | 45.227 |
| fthnc_r1 | None | 0.583 | 0.414 | 1.042 | 1.159 | 813.333 | 0.917 | 0.625 | 0.000 | 6.250 | 3.750 | 1.500 | 0.750 | 59.601 |

DEV temporal-window sweep (G3 DEV clips: det + neg, plus G3 devneg clip; no classifier). C = G3 control, A = A1; wN = temporal window N:

| run | det_seg | det_frame | flick_static | flick_all | ttfc_p90 | fa_devneg | fa_devneg2 |
|---|---|---|---|---|---|---|---|
| A_base | 0.583 | 0.394 | 0.833 | 1.885 | 3333.334 | 0.250 | 0.250 |
| A_w3 | 0.583 | 0.383 | 1.042 | 0.943 | 3366.666 | 0.000 | 0.000 |
| A_w5 | 0.583 | 0.366 | 0.625 | 0.838 | 3433.333 | 0.000 | 0.000 |
| C_base | 0.542 | 0.436 | 5.000 | 4.190 | 733.333 | 0.750 | 0.750 |
| C_w3 | 0.583 | 0.435 | 1.042 | 0.943 | 920.000 | 0.500 | 0.500 |
| C_w5 | 0.542 | 0.415 | 0.417 | 0.628 | 1013.333 | 0.250 | 0.250 |
