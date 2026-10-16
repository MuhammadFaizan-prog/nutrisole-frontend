Device: sandbox CPU (2-core aarch64, shared), PyTorch .pt eval via ml/eval/eval_det.py, imgsz 480, conf 0.001, iou 0.7. G3 rows are the historical G3/G4/G5 eval files (same script and settings). `test_rf_nostrips` and `test_small6` (GT boxes < 6 px at 480 removed) are VIEWs, never replacing the locked splits.

| model | test (n=557) mAP50 / 50-95 | test_rf (n=149) mAP50 / 50-95 | test_oiv7 (n=123) mAP50 / 50-95 | test_oiv7c (n=181) mAP50 / 50-95 | pooled (n=829) mAP50 / 50-95 | test_rf_nostrips (n=149) mAP50 / 50-95 | test_small6 (n=557) mAP50 / 50-95 | neg_test img FA (n=80) |
|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | 0.224 / 0.139 | 0.355 / 0.231 | 0.381 / 0.282 | 0.634 / 0.448 | 0.314 / 0.218 | 0.404 / 0.263 | 0.249 / 0.154 | 0.025 |
| G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx] | 0.218 / 0.139 | 0.359 / 0.239 | 0.429 / 0.314 | 0.784 / 0.579 | 0.310 / 0.217 | 0.409 / 0.273 | 0.242 / 0.153 | 0.0125 |
| G7 sA (rpx mix, from scratch, G3 recipe, seed 0) [G7sA] | 0.199 / 0.124 | 0.380 / 0.255 | 0.485 / 0.298 | 0.671 / 0.510 | 0.282 / 0.192 | 0.424 / 0.286 | 0.221 / 0.137 | 0.0125 |
| G7 sB (rpx mix, from scratch, G3 recipe, seed 1) [G7sB] | 0.209 / 0.131 | 0.385 / 0.262 | 0.523 / 0.352 | 0.675 / 0.533 | 0.286 / 0.198 | 0.435 / 0.298 | 0.232 / 0.145 | 0.0125 |
| G7 rfs (rpx mix, from scratch, G3 recipe, seed 0, repeat-factor sampling) [G7rfs] | 0.224 / 0.141 | 0.376 / 0.251 | 0.380 / 0.288 | 0.773 / 0.581 | 0.311 / 0.218 | 0.423 / 0.283 | 0.248 / 0.155 | 0.025 |

Kaggle-side evals (inside the training kernel, imgsz 480, device as listed; not CPU):

- G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx]: val mAP50 0.4726 / 0.3591 (n=727, Tesla T4)
- G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx]: test_guava mAP50 0.9317 / 0.7495 (n=121, Tesla T4)
- G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx]: test_capsicum_whole mAP50 0.7529 / 0.3168 (n=12, Tesla T4)
- G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx]: train {'gpu': 'Tesla T4', 'train_wall_s': 1893.9, 'data_counts': {'audit_removed_from_train': 0, 'train': 4927, 'val': 727, 'test_guava': 121, 'test_capsicum_whole': 12, 'train_instances': {'capsicum': 1760, 'potato': 698, 'carrot': 3293, 'tomato': 3231, 'lemon_lime': 1966, 'apple': 2935, 'banana': 3846, 'citrus': 5461, 'cucumber': 1074, 'guava': 324, 'pomegranate': 540, 'mango': 276}, 'train_backgrounds': 1005}}
- G7 sA (rpx mix, from scratch, G3 recipe, seed 0) [G7sA]: val mAP50 0.4633 / 0.3372 (n=727, Tesla T4)
- G7 sA (rpx mix, from scratch, G3 recipe, seed 0) [G7sA]: test_guava mAP50 0.9416 / 0.748 (n=121, Tesla T4)
- G7 sA (rpx mix, from scratch, G3 recipe, seed 0) [G7sA]: test_capsicum_whole mAP50 0.7637 / 0.3678 (n=12, Tesla T4)
- G7 sA (rpx mix, from scratch, G3 recipe, seed 0) [G7sA]: train {'gpu': 'Tesla T4', 'train_wall_s': 4541.6, 'data_counts': {'audit_removed_from_train': 0, 'train': 4927, 'val': 727, 'test_guava': 121, 'test_capsicum_whole': 12, 'train_instances': {'capsicum': 1760, 'potato': 698, 'carrot': 3293, 'tomato': 3231, 'lemon_lime': 1966, 'apple': 2935, 'banana': 3846, 'citrus': 5461, 'cucumber': 1074, 'guava': 324, 'pomegranate': 540, 'mango': 276}, 'train_backgrounds': 1005}}
- G7 sB (rpx mix, from scratch, G3 recipe, seed 1) [G7sB]: val mAP50 0.4874 / 0.3641 (n=727, Tesla T4)
- G7 sB (rpx mix, from scratch, G3 recipe, seed 1) [G7sB]: test_guava mAP50 0.9488 / 0.7707 (n=121, Tesla T4)
- G7 sB (rpx mix, from scratch, G3 recipe, seed 1) [G7sB]: test_capsicum_whole mAP50 0.8187 / 0.3775 (n=12, Tesla T4)
- G7 sB (rpx mix, from scratch, G3 recipe, seed 1) [G7sB]: train {'gpu': 'Tesla T4', 'train_wall_s': 6179.8, 'data_counts': {'audit_removed_from_train': 0, 'train': 4927, 'val': 727, 'test_guava': 121, 'test_capsicum_whole': 12, 'train_instances': {'capsicum': 1760, 'potato': 698, 'carrot': 3293, 'tomato': 3231, 'lemon_lime': 1966, 'apple': 2935, 'banana': 3846, 'citrus': 5461, 'cucumber': 1074, 'guava': 324, 'pomegranate': 540, 'mango': 276}, 'train_backgrounds': 1005}}
- G7 rfs (rpx mix, from scratch, G3 recipe, seed 0, repeat-factor sampling) [G7rfs]: val mAP50 0.4889 / 0.3642 (n=727, Tesla T4)
- G7 rfs (rpx mix, from scratch, G3 recipe, seed 0, repeat-factor sampling) [G7rfs]: test_guava mAP50 0.9615 / 0.7732 (n=121, Tesla T4)
- G7 rfs (rpx mix, from scratch, G3 recipe, seed 0, repeat-factor sampling) [G7rfs]: test_capsicum_whole mAP50 0.8042 / 0.3606 (n=12, Tesla T4)
- G7 rfs (rpx mix, from scratch, G3 recipe, seed 0, repeat-factor sampling) [G7rfs]: train {'gpu': 'Tesla T4', 'train_wall_s': 6276.0, 'data_counts': {'audit_removed_from_train': 0, 'rfs': {'t': 0.15, 'class_img_freq': {'banana': 0.1013, 'apple': 0.0917, 'mango': 0.017, 'citrus': 0.1575, 'guava': 0.0609, 'pomegranate': 0.0365, 'lemon_lime': 0.138, 'tomato': 0.0913, 'potato': 0.0154, 'cucumber': 0.0848, 'carrot': 0.0694, 'capsicum': 0.0785}, 'class_repeat': {'banana': 1.217, 'apple': 1.279, 'mango': 2.966, 'citrus': 1.0, 'guava': 1.57, 'pomegranate': 2.026, 'lemon_lime': 1.043, 'tomato': 1.282, 'potato': 3.118, 'cucumber': 1.33, 'carrot': 1.47, 'capsicum': 1.382}, 'g3_apple_tomato_floor': 1.383, 'unique_train': 4927, 'sampled_train': 6380}, 'train': 6380, 'val': 727, 'test_guava': 121, 'test_capsicum_whole': 12, 'train_instances': {'capsicum': 2357, 'potato': 2219, 'carrot': 5262, 'tomato': 4651, 'lemon_lime': 2096, 'apple': 4113, 'banana': 4692, 'citrus': 5826, 'cucumber': 1427, 'guava': 509, 'pomegranate': 1093, 'mango': 822}, 'train_backgrounds': 1005}}

Per-class mAP50, test_rf (instances in brackets):

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | 0.84 (75) | 0.27 (25) | - | 0.67 (34) | - | - | 0.02 (4) | 0.68 (122) | - | 0.05 (73) | 0.30 (84) | 0.02 (110) |
| G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx] | 0.82 (75) | 0.20 (25) | - | 0.78 (34) | - | - | 0.04 (4) | 0.65 (122) | - | 0.04 (73) | 0.34 (84) | 0.01 (110) |
| G7 sA (rpx mix, from scratch, G3 recipe, seed 0) [G7sA] | 0.70 (75) | 0.21 (25) | - | 0.86 (34) | - | - | 0.14 (4) | 0.59 (122) | - | 0.05 (73) | 0.42 (84) | 0.07 (110) |
| G7 sB (rpx mix, from scratch, G3 recipe, seed 1) [G7sB] | 0.74 (75) | 0.20 (25) | - | 0.91 (34) | - | - | 0.10 (4) | 0.58 (122) | - | 0.08 (73) | 0.45 (84) | 0.03 (110) |
| G7 rfs (rpx mix, from scratch, G3 recipe, seed 0, repeat-factor sampling) [G7rfs] | 0.71 (75) | 0.35 (25) | - | 0.78 (34) | - | - | 0.11 (4) | 0.57 (122) | - | 0.09 (73) | 0.35 (84) | 0.05 (110) |

Per-class mAP50, test_oiv7 (instances in brackets):

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | - | 0.08 (1) | 0.41 (22) | 0.33 (1) | - | 0.76 (48) | - | 0.21 (41) | - | 0.49 (173) | 0.01 (3) | 0.76 (120) |
| G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx] | - | 0.20 (1) | 0.40 (22) | 0.50 (1) | - | 0.75 (48) | - | 0.21 (41) | - | 0.57 (173) | 0.00 (3) | 0.80 (120) |
| G7 sA (rpx mix, from scratch, G3 recipe, seed 0) [G7sA] | - | 0.06 (1) | 0.43 (22) | 0.99 (1) | - | 0.80 (48) | - | 0.16 (41) | - | 0.58 (173) | 0.06 (3) | 0.80 (120) |
| G7 sB (rpx mix, from scratch, G3 recipe, seed 1) [G7sB] | - | 0.50 (1) | 0.30 (22) | 0.99 (1) | - | 0.72 (48) | - | 0.26 (41) | - | 0.56 (173) | 0.05 (3) | 0.80 (120) |
| G7 rfs (rpx mix, from scratch, G3 recipe, seed 0, repeat-factor sampling) [G7rfs] | - | 0.08 (1) | 0.45 (22) | 0.20 (1) | - | 0.76 (48) | - | 0.15 (41) | - | 0.57 (173) | 0.01 (3) | 0.82 (120) |

Per-class mAP50, test_oiv7c (instances in brackets):

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | - | 0.53 (6) | - | 0.45 (606) | - | - | 0.46 (299) | 0.74 (4) | - | - | 0.99 (4) | - |
| G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx] | - | 0.74 (6) | - | 0.53 (606) | - | - | 0.75 (299) | 0.91 (4) | - | - | 0.99 (4) | - |
| G7 sA (rpx mix, from scratch, G3 recipe, seed 0) [G7sA] | - | 0.74 (6) | - | 0.56 (606) | - | - | 0.79 (299) | 0.37 (4) | - | - | 0.90 (4) | - |
| G7 sB (rpx mix, from scratch, G3 recipe, seed 1) [G7sB] | - | 0.52 (6) | - | 0.55 (606) | - | - | 0.77 (299) | 0.69 (4) | - | - | 0.84 (4) | - |
| G7 rfs (rpx mix, from scratch, G3 recipe, seed 0, repeat-factor sampling) [G7rfs] | - | 0.75 (6) | - | 0.55 (606) | - | - | 0.78 (299) | 0.89 (4) | - | - | 0.90 (4) | - |

Per-class mAP50, pooled (instances in brackets):

| model | banana | apple | mango | citrus | guava | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3 control (CHAMPION; historical eval files) | 0.34 (5123) | 0.25 (2148) | 0.36 (22) | 0.45 (1868) | - | 0.72 (48) | 0.02 (294) | 0.39 (822) | 0.14 (366) | 0.24 (357) | 0.31 (1645) | 0.22 (510) |
| G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx] | 0.33 (5123) | 0.20 (2148) | 0.37 (22) | 0.46 (1868) | - | 0.69 (48) | 0.06 (294) | 0.39 (822) | 0.08 (366) | 0.29 (357) | 0.32 (1645) | 0.23 (510) |
| G7 sA (rpx mix, from scratch, G3 recipe, seed 0) [G7sA] | 0.30 (5123) | 0.17 (2148) | 0.23 (22) | 0.43 (1868) | - | 0.67 (48) | 0.08 (294) | 0.33 (822) | 0.05 (366) | 0.30 (357) | 0.30 (1645) | 0.24 (510) |
| G7 sB (rpx mix, from scratch, G3 recipe, seed 1) [G7sB] | 0.31 (5123) | 0.15 (2148) | 0.21 (22) | 0.46 (1868) | - | 0.64 (48) | 0.07 (294) | 0.37 (822) | 0.07 (366) | 0.29 (357) | 0.34 (1645) | 0.24 (510) |
| G7 rfs (rpx mix, from scratch, G3 recipe, seed 0, repeat-factor sampling) [G7rfs] | 0.31 (5123) | 0.22 (2148) | 0.33 (22) | 0.48 (1868) | - | 0.70 (48) | 0.06 (294) | 0.36 (822) | 0.09 (366) | 0.32 (357) | 0.31 (1645) | 0.25 (510) |

Strict rule (pre-registered): a supported class dropping > 0.02 mAP50 vs G3 on test_rf, test_oiv7 or test_oiv7c (classes with < 20 instances in a split are reported but not gated):

- G6 rpx (G3-init fine-tune; reference, single seed) [G6rpx]: pooled 0.3097 (> 0.314: False); per-class fails {'test_rf/apple': -0.0701, 'test_rf/tomato': -0.023} -> image gates FAIL
- G7 sA (rpx mix, from scratch, G3 recipe, seed 0) [G7sA]: pooled 0.2819 (> 0.314: False); per-class fails {'test_rf/banana': -0.1312, 'test_rf/apple': -0.0583, 'test_rf/tomato': -0.0864, 'test_oiv7/tomato': -0.0561} -> image gates FAIL
- G7 sB (rpx mix, from scratch, G3 recipe, seed 1) [G7sB]: pooled 0.2859 (> 0.314: False); per-class fails {'test_rf/banana': -0.099, 'test_rf/apple': -0.072, 'test_rf/tomato': -0.096} -> image gates FAIL
- G7 rfs (rpx mix, from scratch, G3 recipe, seed 0, repeat-factor sampling) [G7rfs]: pooled 0.3107 (> 0.314: False); per-class fails {'test_rf/banana': -0.1221, 'test_rf/tomato': -0.1035, 'test_oiv7/tomato': -0.0641} -> image gates FAIL

Fixed-frame TEST gauntlet (stride 1; G1 det/quality/neg + G2 negtest clips; sandbox CPU shared; det imgsz 480; cls G3 E224 T=0.25; guard rule 2 off). Latency is sandbox CPU under load, not phone:

| run | tracker | det_seg | det_frame | flick_static | id_switches | ids_per_seg | ttfc_p50 | ttfc_p90 | q_acc | rot_rec | grade_flick | fa_g1neg | fa_negtest | full_p50_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G4 G3champ_msc0 r1 (historical) | iou | 0.667 | 0.496 | 0.000 | None | None | 466.667 | 760.000 | 0.929 | 0.875 | 0.000 | 1.250 | 0.000 | 47.211 |
| G6 G3 control + IouTracker r1 | iou | 0.667 | 0.496 | 0.000 | 43 | 1.458 | 466.667 | 760.000 | 0.929 | 0.875 | 0.000 | 1.250 | 0.000 | 45.840 |
| G6 G3 control + ByteTrack r1 | bytetrack | 0.667 | 0.532 | 0.000 | 30 | 1.208 | 533.333 | 933.333 | 0.929 | 0.875 | 0.000 | 1.250 | 0.000 | 46.351 |
| G6 G3 control + ByteTrack r2 | bytetrack | 0.667 | 0.532 | 0.000 | 30 | 1.208 | 533.333 | 933.333 | 0.929 | 0.875 | 0.000 | 1.250 | 0.000 | 63.632 |
