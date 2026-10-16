# G9 Stage J5 (cv-gauntlet-device): push the three ONNX weights to the phone for the debug CV pipeline. Run on the user's Windows PC.
# Usage (repo root, PowerShell):  powershell -ExecutionPolicy Bypass -File native/scripts/g9j5-push-models.ps1 -Dir models_g9j5
# The files come from NutriSole_G9J5_device_models.zip (handoff). Weights are never committed to Git and never bundled in the APK.
param([string]$Dir = "models_g9j5")
$ErrorActionPreference = "Stop"
$pkg = "com.muhammadfaizan.nutrisole"; $dst = "/sdcard/Android/data/$pkg/files/models"
$want = @{
  "h2_mnv3s.onnx"            = "20898d7cdfc1f0580cdf3f58d6d3d63528b9c04178d4603b49dee4ba1b89a22e";
  "det_yolo11n_640_raw.onnx" = "c6fcb32a5fb2f51ba34e88ce9106a52d6bbd12ae385ca8361b292d54e3d340c1";
  "E_224_e15_b64_sgd01.onnx" = "c51d21994444d2a5a43907cae66a36ac7fb63b19b1198dda891f24af751f709b"
}
if (-not (Get-Command adb -ErrorAction SilentlyContinue)) { Write-Error "adb not found: install Android platform-tools and add it to PATH" }
if (-not (adb devices | Select-String "device$")) { Write-Error "no phone attached (enable USB debugging and accept the prompt on the phone)" }
foreach ($f in $want.Keys) {
  $p = Join-Path $Dir $f
  if (-not (Test-Path $p)) { Write-Error "missing $p (unzip NutriSole_G9J5_device_models.zip into $Dir)" }
  $h = (Get-FileHash -Algorithm SHA256 $p).Hash.ToLower()
  if ($h -ne $want[$f]) { Write-Error "$f sha256 $h does not match $($want[$f])" }
  Write-Host "OK  $f  $h"
}
adb shell mkdir -p $dst
foreach ($f in $want.Keys) { adb push (Join-Path $Dir $f) "$dst/$f" }
adb shell ls -l $dst
Write-Host "Models pushed to $dst. If 'Permission denied': open the app once, close it, and run this script again."
