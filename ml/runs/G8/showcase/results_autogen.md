# G8 showcase results (autogen by decide.py)

Rule: G8_prereg.md Addendum 2026-10-13 S3; target 0.6; pooled n=829, CPU, imgsz 480, conf 0.001, iou 0.7. G3 numbers = historical CPU eval file ml/runs/G3/eval_pooled_k11_480.

| class | inst | G3 AP50 | s0 AP50 | s1 AP50 | G3 R | s0 R | G3 AP50-95 | s0 AP50-95 | s0 pass |
|---|---|---|---|---|---|---|---|---|---|
| citrus | 1868 | 0.4512 | 0.4616 | 0.4575 | 0.4325 | 0.4695 | 0.3188 | 0.3308 | False |
| apple | 2148 | 0.2472 | 0.2633 | 0.2818 | 0.2081 | 0.2408 | 0.1571 | 0.1803 | False |
| banana | 5123 | 0.3407 | 0.3417 | 0.3303 | 0.3881 | 0.3555 | 0.1678 | 0.1728 | False |
| tomato | 822 | 0.3943 | 0.3722 | 0.3543 | 0.4246 | 0.3674 | 0.2574 | 0.248 | False |
| carrot | 1645 | 0.3118 | 0.3269 | 0.3219 | 0.3717 | 0.3596 | 0.1628 | 0.1781 | False |

Video FA/min (g3clips_dev neg, IouTracker): {'G3': 0.75, 'G3r5': 0.5, 'show_s0': 0.0}
Latency: {'G3': {'n': 200, 'p50': 64.05, 'p95': 86.31, 'mean': 65.53}, 'G3r5': {'n': 200, 'p50': 67.52, 'p95': 87.57, 'mean': 72.63}, 'show_s0': {'n': 200, 'p50': 65.85, 'p95': 84.51, 'mean': 68.8}, 'note': 'sandbox CPU (2 cores aarch64, shared), onnxruntime CPU EP, 100 val frames x 2 passes, model order alternated per pass, det session.run only (letterbox excluded)'}
Criteria: {'1_per_class_>=4of5_both_seeds': False, '2_video_fa_min_le_G3r5': True, '3_latency_p95_le_1.10x': True, '4_onnx_parity': True}
**PASS: False**; claimable (seed 0): []
