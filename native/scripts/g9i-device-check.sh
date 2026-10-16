#!/usr/bin/env bash
# G9 Stage I Android check, bash version of g9i-device-check.ps1 (Linux / macOS). Not run in the sandbox (no adb / device).
# Usage: bash native/scripts/g9i-device-check.sh [MINUTES] [APK]
set -euo pipefail; MIN=${1:-3}; APK=${2:-}; OUT=g9i_device_log
echo "== I1 tests"; (cd native && npm test); python3 -m pytest -q ml/eval/test_closeup.py ml/eval/test_verify.py ml/eval/test_camera_io.py ml/prices/tests
command -v adb >/dev/null || { echo "adb not found; stopping after I1"; exit 0; }
adb devices | grep -q "device$" || { echo "no device / emulator; stopping after I1"; exit 0; }
echo "== I2 device: $(adb shell getprop ro.product.model) abi=$(adb shell getprop ro.product.cpu.abi) sdk=$(adb shell getprop ro.build.version.sdk) emulator=$(adb shell getprop ro.kernel.qemu)"
adb shell dumpsys media.camera | grep -E "supportedHardwareLevel|facing" | head -8 || true
[ -n "$APK" ] && adb install -r "$APK"
echo "== I3 parity bundle"; adb shell mkdir -p /sdcard/Download/nscv_parity; for f in ml/runs/G9/stageI/device_parity/*; do adb push "$f" /sdcard/Download/nscv_parity/ >/dev/null; done
echo "== I4 logcat ${MIN} min: run A1-A9 (docs/cv/gauntlet/G9_stageI_android_test.md)"; adb logcat -c
timeout "$((MIN*60))" adb logcat -v epoch -s NSCV:* ReactNativeJS:* > "$OUT.txt" || true
python3 - "$OUT.txt" <<'P'
import re, sys, collections
L = open(sys.argv[1], errors="ignore").read().splitlines(); S = collections.defaultdict(list); E = collections.Counter(); P = []
for l in L:
    m = re.search(r"NSCV.*stage=(\w+).*ms=([\d.]+)", l); m and S[m[1]].append(float(m[2]))
    m = re.search(r"event=(\w+)", l); m and E.update([m[1]])
    m = re.search(r"NSCV parity file=(\S+) maxdiff=([\d.]+)", l); m and P.append(float(m[2]))
for k, v in S.items(): v.sort(); print(f"{k:10s} n={len(v):5d} p50={v[(len(v)-1)//2]:8.1f} p95={v[int(0.95*(len(v)-1))]:8.1f} ms")
print("events", dict(E)); print("parity files", len(P), "over 0.02:", sum(d > 0.02 for d in P)); print("mapping lines", sum("NSCV map " in l for l in L))
P
