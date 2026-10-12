# G6: validation that needs a real Android phone (pending)

Sandbox facts (checked 2026-10-13, `g6logs/env.txt`): 2-core aarch64 CPU, 7.8 GB RAM, no GPU, **no /dev/kvm, no adb, no Android SDK/emulator**, no phone attached. An emulator cannot run here (no hardware virtualisation), so G6.7 was not attempted. Every G6 latency number is **Linux sandbox CPU (onnxruntime, 2 threads)** and must not be read as phone FPS, thermals, battery or camera behaviour.

| # | test | why it needs the phone | how to run (user) | pass criterion (proposal) |
|---|---|---|---|---|
| 1 | Live-camera end-to-end FPS and latency (G3 control, 480, raw+NMS) | camera pipeline, NNAPI/XNNPACK, thermal throttling | dev build, Scan screen, 3 min continuous, on-screen perf overlay / logcat timings | median full-pipeline latency <= 150 ms, no throttling drop > 30% after 3 min |
| 2 | ONNX Runtime Mobile vs sandbox parity on the same frames | different kernels/EPs | replay the 3 G1 fixture frames through the app's dev replay hook, export detections | box IoU >= 0.99, score diff <= 1e-3 vs `ml/runs/G6/*parity*` |
| 3 | Lahore field test (the real benchmark) | real mandi light, sodium lamps, phone optics, hand shake | 15-20 clips of 10-20 s across >= 3 markets/days (banana, apple, tomato, citrus, capsicum, cucumber, carrot, guava; some rotten; half daylight, half shop light), split by market | per-clip labels by a person; segment acc and FA/min reported per market, never mixed with web footage |
| 4 | Tracking UX (IouTracker default vs ByteTrack research option) | perceived stability, delay before first box, ghost boxes | same field clips; only if the Python ByteTrack result justifies a TS port | no extra delay > 100 ms to first box; fewer label/grade flips |
| 5 | Memory and battery | device-only | Android Studio profiler, 10 min scan | no leak; < 5%/10 min battery on a mid-range phone |
| 6 | Night / tube-light classifier behaviour in situ | the held-out lighting families are synthetic or curated photos | field clips in shop lighting | rotten produce graded C/Reject in >= 0.95 of segments |
| 7 | Camera permission, model-load failure, backgrounding/resume | OS behaviour | manual QA checklist | no crash; clear error message |

Carried from G5: none of the above has been run. Nothing in G6 changes this list except item 4 (ByteTrack is evaluated in Python only and is not ported to `native/`).
