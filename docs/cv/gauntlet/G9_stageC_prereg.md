# G9 Stage C: small-object detection and tracking (DEV ONLY), audit and pre-registration

Written 2026-10-14 (PKT) **before any Stage C ablation number was computed**. Authoritative brief: user, 2026-10-14 13:41 PKT
(G3 untouched as champion, no training, no holdout reuse, freeze the best DEV config, final evaluation only on fresh independently
labelled footage). Branch `cv-gauntlet` only.

## 1. Audit of the 1% area guard (code reading only, no results)

**What it is.** Rule 1 of the G3 scene guard: `scene_guard(dets, maxSameClass=0, minAreaFrac=0.01)`,
`ml/eval/scene_guard.py` L15-23 (`DEFAULT_GUARD`), mirrored exactly by `sceneGuard()` / `DEFAULT_SCENE_GUARD` in
`native/src/cv/pipeline/postprocess.ts` L46-60 (parity test `native/tests/cvSceneGuard.test.ts`). Rule 2 (same-class cap) is off (0)
since G4. 0.01 came from the G3 DEV guard tune (`ml/runs/G3/guard_tune_k11_480/guard_tune.json`, `ml/eval/tune_tracker.py guard_grid`): grid
minAreaFrac {0, 0.002, 0.005, 0.01, 0.02} x maxSameClass {0,3,4,6,8}, objective = minimise DEV FA episodes/min subject to segment
accuracy >= no-guard - 2 pp. The objective contained **no small-object recall term**, and DEV had almost no small objects, so 1%
was chosen purely for FA (no guard 1.25 FA tracks/min -> 0.75).

**Where it runs.** Per frame, after model decode + score floor 0.35 + class-wise NMS 0.7 + mapping back to the source frame, and
**before** the IouTracker. Every evaluation replay uses it in that position: `ml/runs/G9/fp/scripts/g9fp_replay.py`,
`ml/runs/G9/stageB/scripts/stageb_dev.py` L49, the holdout kernels and `carrot16.py` L24. A box removed here never reaches the
tracker: it cannot start, extend or keep alive a track (so the guard also interrupts association, see section 4).
In the native app the function exists and is parity-tested, but a repo-wide search of `native/src` finds **no runtime caller**
(`sceneGuard`, `decodeRawWithNms` and `IouTracker` are referenced only from `src/cv/pipeline/*` and `native/tests/*`): the guard is a
pipeline contract implemented in the shared library, not yet wired into a frame processor. Any change is therefore a config value
(`minAreaFrac`) in both mirrors plus the parity fixture.

**What the 1% is computed against.** The **original (source) frame**, not the 480 letterboxed model input. The decode path
(`ml/eval/geometry.py` `letterbox` -> `decode` -> `dst_to_src`, then divide by source W, H; same in `cache_dets*.py` and `carrot16.py`)
removes the letterbox padding and rescales to source pixels before normalising, and the guard multiplies normalised width x height.
Consequences: padding bars never count; the threshold in model-input pixels depends on the source aspect ratio; and it is **smaller
than the 48x48 px a 1%-of-480x480 reading would suggest**.

| source frame | 1% (current) | 0.5% | 0.25% |
|---|---|---|---|
| 480x640 portrait (DEV det/neg clips) | 3072 src px^2 (~55x55 src) = 1728 model px^2 (~41.6x41.6 at 480) | ~39x39 src / ~29.4x29.4 model | ~28x28 src / ~20.8x20.8 model |
| 480x736 portrait (holdout #16, file metadata only) | ~59x59 src / ~38.8x38.8 model | ~42x42 / ~27.4 | ~30x30 / ~19.4 |
| 1080x1920 phone portrait | ~144x144 src / ~36x36 model | ~102x102 / ~25.5 | ~72x72 / ~18.0 |
| 1920x1080 landscape | ~144x144 src / ~36x36 model | ~102x102 / ~25.5 | ~72x72 / ~18.0 |

(Model input = 480 letterbox, content 360x480 / 313x480 / 270x480; "model px" = side of the equal-area square inside the
480 input. G3 was trained at 640 and is deployed at 480, so an object at the guard limit is ~36-42 px at inference, ~0.75x of what
it was at training resolution.) For reference, the YOLO P3 stride is 8 px, so 0.25% (~18-21 px) is ~2.5 grid cells wide.

## 2. Arms (only `minAreaFrac` varies)

| arm | minAreaFrac |
|---|---|
| C0 (= G3, current) | 0.01 |
| C1 | 0.005 |
| C2 | 0.0025 |
| C3 (no guard) | 0 |

Fixed for all arms: G3 YOLO11n weights (`det_yolo11n_640_raw.onnx`, trained 640, run at 480 letterbox), raw decode + class-wise
NMS 0.7, score floor 0.35, rule 2 off, IouTracker defaults (iouMatch 0.3, minHits 2, maxMissed 4, boxAlpha 0.6, scoreAlpha 0.2,
switchMargin 0.15, switchFrames 3, stableIou 0.8, stableMs 500), label hysteresis. No training. Detector outputs are cached once
(deterministic) and every arm is a replay of the same cache.

## 3. Data (DEV only)

- **DEV val stills** (`det_v3/val.txt`, n=402; G3 DEV, used in every G9 stage): per-class P/R at 0.35 / IoU 0.5 after the guard,
  recall by GT size bin, false boxes (unmatched dets) overall and on box-free images.
- **DEV det clip** (`g3clips_dev/det_clip`, 24 segments) and **DEV neg clip** (`neg_clip`, 4.0 min, devneg images): unchanged
  `video_gauntlet.metrics()` + TTFC from first GT visibility (Stage A addendum definition).
- **Synthetic small-object probe (DEV-only, marked SYNTHETIC)**, because DEV has almost no small objects (Stage B found 2):
  val stills downscaled by s in {1/2, 1/3, 1/4} and pasted onto a devneg background (480x640) with a slow linear drift
  (camera-shake proxy, ~3 px/frame), 15 frames per segment at 10 fps, 5 background-only gap frames between segments,
  up to 6 images per class (seed 0), segment class = the class of the image's GT boxes (single-class images only), all GT boxes
  carried. Sources are DEV val stills and DEV negatives only; no holdout, no Stage B mining pool, no new labels.
  Scored with the same `metrics()` (frame recall, IDs/segment, ID switches, fragmentations, TTFC) plus false boxes/tracks in the
  gap frames and unmatched shown tracks inside segments ("mixed-scene false"). It is a proxy: pasted, rescaled stills are not real
  far-away produce, so it can rank arms but it cannot confirm a real-world gain.
- Size bins (GT area as a fraction of the source frame): <0.25%, 0.25-0.5%, 0.5-1%, 1-2.5%, >=2.5%.
- **Holdout**: carrot #16's existing Stage B trace is read for diagnosis only. No holdout clip is re-run and nothing is tuned on it.

## 4. Metrics reported per arm

Per-class frame recall (DEV det clip and probe; carrot and the 5 showcase classes citrus, apple, banana, tomato, carrot), val
per-class R, small-object recall by size bin (val + probe), FA/min = false-alarm episodes/min on the DEV neg clip, displayed
tracks/min on DEV negatives (distinct shown track IDs/min), fragmented tracks (distinct IDs per GT segment, fragmentations),
ID switches, TTFC p50/p90, postprocess+tracker CPU per frame p50/p95 (the detector is identical across arms; its sandbox latency is
`ml/runs/G9/stageB/latency_sandbox.json`, B0 p50 55.9 / p95 95.5 ms). For every arm, **"+k produce recovered, +N false" vs C0**:
extra true matches (val TP, probe frames) next to extra false boxes (val unmatched, box-free), extra false tracks (DEV neg) and extra
mixed-scene false tracks (probe).

**Raw vs discarded**: count of G3 boxes >= 0.35 before and after each guard, by class and size bin, on val, DEV det, DEV neg and
the probe, split into boxes that match a GT (IoU >= 0.5, same class) and boxes that do not.

## 5. Selection rule (fixed now)

An arm is admissible only if, vs C0:
1. no showcase class loses more than **2 pp** of frame recall on the DEV det clip, nor more than 2 pp of val R;
2. FA/min (episodes/min, DEV neg) <= C0 + **0.25/min** (one extra episode in the 4-min clip);
3. displayed tracks/min on DEV negatives <= C0 + **0.25/min** (one extra false track in 4 min);
4. val box-free false boxes <= C0 + **2**, and probe mixed-scene false tracks per minute <= C0 x **1.10**;
5. TTFC p90 on the DEV det clip not worse than C0 + 100 ms.

Among admissible arms the pick is the one with the largest gain in **probe frame recall on showcase classes for GT < 1% of the frame**;
the gain must be >= **3 pp** over C0, otherwise C0 stays. Gains within 1 pp of each other tie, and ties go to the larger
`minAreaFrac` (more conservative). Any change that buys small-object recall by flooding false detections fails rules 2-4.

## 6. Fragmentation analysis (analysis only, no gate, nothing promoted)

On the picked guard and on C0, replay the DEV det clip, the probe and the DEV neg clip with: IouTracker iouMatch 0.3 (current),
0.2, and 0.3 + a centre-distance fallback for small boxes (after IoU matching, an unmatched track and an unmatched detection whose
boxes are both < 2% of the frame are associated if their centre distance <= 1.0 x the mean side of the two boxes; greedy by
distance). Report IDs per GT segment, ID switches, fragmentations, frame recall and neg false tracks. Recommendation only.

## 7. Outputs

`ml/runs/G9/stageC/` (scripts, caches summary, per-arm JSON), frozen DEV config `ml/runs/G9/stageC/frozen_dev_config.json`,
report `docs/cv/gauntlet/G9_stageC.md`. The frozen config is a DEV pick only: final evaluation awaits fresh, independently labelled
footage; the existing holdout is not touched. G3 remains champion.
