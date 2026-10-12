# G2 failure analysis

Sources: `ml/runs/G2/failures_g2/failures.json` (+ det_worst.jpg, cls_worst.jpg), eval_det_k11 / eval_det_k26_e2e, the gauntlet_* runs, and the grading_proxy*. Detector failures: yolo11n best.pt at 480 on the locked TEST split (557 images, 12 267 GT boxes).

## 1. Detector data ceiling (largest)
- **Missed boxes:** 8 161 of 12 267 (67%). By class:
  - banana: 3 471/5 048
  - apple: 1 459/2 122
  - carrot: 1 157/1 558
  - citrus: 785/1 833
  - tomato: 471/659
  - potato: 259/366
  - capsicum: 257/280
  - lemon_lime: 193/290
  - cucumber: 109/111
- **Where they come from:** most misses are small instances in crowded LVIS market and kitchen scenes. LVIS is federated, so images are not exhaustively labelled. This means some "false" boxes are real fruit, and training is penalised for finding them.
- **False and wrong-class boxes:** 1 527 false boxes and 231 wrong-class boxes. Top confusions:
  - citrus -> lemon_lime: 46
  - lemon_lime -> citrus: 40
  - carrot -> tomato: 23
  - apple -> citrus: 20
  - citrus -> apple: 16
- **test_rf (149 Roboflow-style photos, closest to the app use-case):** at deploy sizes this barely moved vs G1 (0.32 -> 0.32/0.37), and lemon_lime regressed.
  - GPU training plus full data doubled test mAP (crowded scenes) but not test_rf (single items).
  - Training at 640 then deploying at 384/480 loses about 0.03-0.05.
- **Missing classes:** mango, guava and pomegranate are absent. In the quality clip, guava and pomegranate segments are therefore never detected (recall 0), which caps gauntlet quality segment accuracy at about 50%.

## 2. False alarms on texture and clutter
- **On the G1 negative clip (coco128 + plain backgrounds):**
  - G1 detector: 3.75 FA/min
  - G2 yolo11n raw 480: 42.5 FA/min
  - G2 yolo26n e2e 384: 136 FA/min
- **The dominant source is one stadium frame.** About 30 rows of red seats each became a confident "tomato" track (see `gauntlet_yolo26n_e2e_384/neg_annotated.mp4`). There is also a large red/brown box at the clip edge on a plain background.
- **New 2.7 min negtest clip:** 5.25 FA/min (yolo11n) and 6.38 FA/min (yolo26n). Both are above the gate of 1/min.
- **Still-image FA rate is low** (2.5-3.75% of 80 neg images). The video metric is dominated by repeated textures and track fragmentation: every frame's box can mint a new track id.
- **Cause (inferred):** the det-v2 negatives are COCO scenes without produce. They contain few repetitive red/round textures (seats, balls, lights). The 640 training on crowded piles teaches "many small round red things = tomato".

## 3. Quality classifier: crop and lighting gap
- **Full images:** the G2 192 model gets rotten recall 0.992, the same as G1.
- **Detector-style item crops (grading proxy):** rotten recall falls to 0.941 (G1: 0.983). 7 rotten crops were graded A/B.
- **Tube-light WB:** rotten recall drops 0.966 -> 0.941.
- **Errors on full images:** 2/270 (guava rotten -> fresh, p_true 0.13; orange fresh -> rotten). Guava rotten is the hardest class.
- **Kaggle 224 run** (60 ep, batch 128, hsv_v 0.5, erasing 0.2): 0.948 acc. That is worse than the 15-epoch CPU 192 run, and ECE got worse after temperature scaling (0.021 -> 0.027). The recipe probably over-regularised or overfit the augmented copies (inferred). It needs a LR/epoch sweep on val.
- **Gauntlet rotten segment recall** swings between 0.625 and 0.875 across runs. With only 8 rotten segments, one segment moves it by 0.125, so this is a small-sample result.
- **3-level (quarantined):** mild recall 0.242. Mild is not separable with Sultana + FruQ-DB labels.

## Smaller issues
- **Gauntlet latency is contaminated** when the CPU is shared (load average about 10 during some runs). The G1-detector-under-G2-tracker run dropped 45% of frames, so its flicker/TTFC are not comparable. G3 must run gauntlets on an idle CPU, sequentially.
- **Quality-clip flicker with yolo11n raw** is 5.0 /10s: class switching between citrus and lemon_lime on close-ups. yolo26n e2e had 0.0, but it detects less.
- **Sandbox restarts** (3 during G2) wipe /tmp. All scripts are idempotent, but long CPU jobs are lost.
