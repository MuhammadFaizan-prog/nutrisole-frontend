Device: sandbox CPU (2-core aarch64, shared), PyTorch .pt eval via ml/eval/eval_det.py, imgsz 480, conf 0.001, iou 0.7. G3 rows are the historical G3/G4/G5 eval files (same script and settings). `test_rf_nostrips` and `test_small6` (GT boxes < 6 px at 480 removed) are VIEWs, never replacing the locked splits.

| model | test (n=557) mAP50 / 50-95 | test_rf (n=149) mAP50 / 50-95 | test_oiv7 (n=123) mAP50 / 50-95 | test_oiv7c (n=181) mAP50 / 50-95 | pooled (n=829) mAP50 / 50-95 | test_rf_nostrips (n=149) mAP50 / 50-95 | test_small6 (n=557) mAP50 / 50-95 | neg_test img FA (n=80) |
|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | 0.224 / 0.139 | 0.355 / 0.231 | 0.381 / 0.282 | 0.634 / 0.448 | 0.314 / 0.218 | 0.404 / 0.263 | 0.249 / 0.154 | 0.025 |
| G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx] | 0.218 / 0.139 | 0.359 / 0.239 | 0.429 / 0.314 | 0.784 / 0.579 | 0.310 / 0.217 | 0.409 / 0.273 | - | 0.0125 |

Kaggle-side evals (inside the training kernel, imgsz 480, device as listed; not CPU):

- G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx]: val mAP50 0.4726 / 0.3591 (n=727, Tesla T4)
- G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx]: test_guava mAP50 0.9317 / 0.7495 (n=121, Tesla T4)
- G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx]: test_capsicum_whole mAP50 0.7529 / 0.3168 (n=12, Tesla T4)
- G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx]: train {'gpu': 'Tesla T4', 'train_wall_s': 1893.9, 'data_counts': {'audit_removed_from_train': 0, 'train': 4927, 'val': 727, 'test_guava': 121, 'test_capsicum_whole': 12, 'train_instances': {'capsicum': 1760, 'potato': 698, 'carrot': 3293, 'tomato': 3231, 'lemon_lime': 1966, 'apple': 2935, 'banana': 3846, 'citrus': 5461, 'cucumber': 1074, 'guava': 324, 'pomegranate': 540, 'mango': 276}, 'train_backgrounds': 1005}}

Per-class mAP50, test_rf (instances in brackets):

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | 0.84 (75) | 0.27 (25) | - | 0.67 (34) | - | - | 0.02 (4) | 0.68 (122) | - | 0.05 (73) | 0.30 (84) | 0.02 (110) |
| G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx] | 0.82 (75) | 0.20 (25) | - | 0.78 (34) | - | - | 0.04 (4) | 0.65 (122) | - | 0.04 (73) | 0.34 (84) | 0.01 (110) |

Per-class mAP50, test_oiv7 (instances in brackets):

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | - | 0.08 (1) | 0.41 (22) | 0.33 (1) | - | 0.76 (48) | - | 0.21 (41) | - | 0.49 (173) | 0.01 (3) | 0.76 (120) |
| G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx] | - | 0.20 (1) | 0.40 (22) | 0.50 (1) | - | 0.75 (48) | - | 0.21 (41) | - | 0.57 (173) | 0.00 (3) | 0.80 (120) |

Per-class mAP50, test_oiv7c (instances in brackets):

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | - | 0.53 (6) | - | 0.45 (606) | - | - | 0.46 (299) | 0.74 (4) | - | - | 0.99 (4) | - |
| G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx] | - | 0.74 (6) | - | 0.53 (606) | - | - | 0.75 (299) | 0.91 (4) | - | - | 0.99 (4) | - |

Per-class mAP50, pooled (instances in brackets):

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | 0.34 (5123) | 0.25 (2148) | 0.36 (22) | 0.45 (1868) | - | 0.72 (48) | 0.02 (294) | 0.39 (822) | 0.14 (366) | 0.24 (357) | 0.31 (1645) | 0.22 (510) |
| G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx] | 0.33 (5123) | 0.20 (2148) | 0.37 (22) | 0.46 (1868) | - | 0.69 (48) | 0.06 (294) | 0.39 (822) | 0.08 (366) | 0.29 (357) | 0.32 (1645) | 0.23 (510) |

Strict rule (pre-registered): a supported class dropping > 0.02 mAP50 vs G3 on test_rf, test_oiv7 or test_oiv7c (classes with < 20 instances in a split are reported but not gated):

- G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx]: pooled 0.3097 (> 0.314: False); per-class fails {'test_rf/apple': -0.0701, 'test_rf/tomato': -0.023} -> image gates FAIL

Fixed-frame TEST gauntlet (stride 1; G1 det/quality/neg + G2 negtest clips; sandbox CPU shared; det imgsz 480; cls G3 E224 T=0.25; guard rule 2 off). Latency is sandbox CPU under load, not phone:

| run | tracker | det_seg | det_frame | flick_static | id_switches | ids_per_seg | ttfc_p50 | ttfc_p90 | q_acc | rot_rec | grade_flick | fa_g1neg | fa_negtest | full_p50_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G4 G3champ_msc0 r1 (historical) | iou | 0.667 | 0.496 | 0.000 | None | None | 466.667 | 760.000 | 0.929 | 0.875 | 0.000 | 1.250 | 0.000 | 47.211 |
| G6 G3 control + IouTracker r1 | iou | 0.667 | 0.496 | 0.000 | 43 | 1.458 | 466.667 | 760.000 | 0.929 | 0.875 | 0.000 | 1.250 | 0.000 | 45.840 |
| G6 G3 control + ByteTrack r1 | bytetrack | 0.667 | 0.532 | 0.000 | 30 | 1.208 | 533.333 | 933.333 | 0.929 | 0.875 | 0.000 | 1.250 | 0.000 | 46.351 |
| G6 G3 control + ByteTrack r2 | bytetrack | 0.667 | 0.532 | 0.000 | 30 | 1.208 | 533.333 | 933.333 | 0.929 | 0.875 | 0.000 | 1.250 | 0.000 | 63.632 |
