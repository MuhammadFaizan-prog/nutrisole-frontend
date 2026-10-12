Device: sandbox CPU (2-core aarch64, shared), PyTorch .pt eval via ml/eval/eval_det.py, imgsz 480, conf 0.001, iou 0.7. G3 rows are the historical G3/G4/G5 eval files (same script and settings). `test_rf_nostrips` is a VIEW.

| model | test (n=557) mAP50 / 50-95 | test_rf (n=149) mAP50 / 50-95 | test_oiv7 (n=123) mAP50 / 50-95 | test_oiv7c (n=181) mAP50 / 50-95 | pooled (n=829) mAP50 / 50-95 | test_rf_nostrips (n=149) mAP50 / 50-95 | neg_test img FA (n=80) |
|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | 0.224 / 0.139 | 0.355 / 0.231 | 0.381 / 0.282 | 0.634 / 0.448 | 0.314 / 0.218 | 0.404 / 0.263 | 0.025 |

Kaggle-side evals (inside the training kernel, imgsz 480, device as listed; not CPU):


Per-class mAP50, test_rf (instances in brackets):

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | 0.84 (75) | 0.27 (25) | - | 0.67 (34) | - | - | 0.02 (4) | 0.68 (122) | - | 0.05 (73) | 0.30 (84) | 0.02 (110) |

Per-class mAP50, test_oiv7 (instances in brackets):

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | - | 0.08 (1) | 0.41 (22) | 0.33 (1) | - | 0.76 (48) | - | 0.21 (41) | - | 0.49 (173) | 0.01 (3) | 0.76 (120) |

Per-class mAP50, test_oiv7c (instances in brackets):

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | - | 0.53 (6) | - | 0.45 (606) | - | - | 0.46 (299) | 0.74 (4) | - | - | 0.99 (4) | - |

Per-class mAP50, pooled (instances in brackets):

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | 0.34 (5123) | 0.25 (2148) | 0.36 (22) | 0.45 (1868) | - | 0.72 (48) | 0.02 (294) | 0.39 (822) | 0.14 (366) | 0.24 (357) | 0.31 (1645) | 0.22 (510) |

Strict rule (pre-registered): a supported class dropping > 0.02 mAP50 vs G3 on test_rf, test_oiv7 or test_oiv7c (classes with < 20 instances in a split are reported but not gated):


Fixed-frame TEST gauntlet (stride 1; G1 det/quality/neg + G2 negtest clips; sandbox CPU shared; det imgsz 480; cls G3 E224 T=0.25; guard rule 2 off). Latency is sandbox CPU under load, not phone:

| run | tracker | det_seg | det_frame | flick_static | id_switches | ids_per_seg | ttfc_p50 | ttfc_p90 | q_acc | rot_rec | grade_flick | fa_g1neg | fa_negtest | full_p50_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G4 G3champ_msc0 r1 (historical) | iou | 0.667 | 0.496 | 0.000 | None | None | 466.667 | 760.000 | 0.929 | 0.875 | 0.000 | 1.250 | 0.000 | 47.211 |

DEV tracker grid (G3 control; DEV det clip, 24 segments; sandbox CPU):

| run | det_seg | flick_static | id_switches | ttfc_p90 |
|---|---|---|---|---|
| IouTracker (G6 dev_iou) | 0.542 | 5.000 | 68 | 733.333 |
