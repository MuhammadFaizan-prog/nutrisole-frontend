# G9 Stage I Android check (extends g9h-device-check.ps1) for the user's Windows PC. NOT run in the sandbox (no adb / SDK / device).
# Usage (PowerShell, repo root):  powershell -ExecutionPolicy Bypass -File native/scripts/g9i-device-check.ps1 [-Minutes 3] [-Apk path]
# I1 tests (TS + Python, incl. cvCamera parity); I2 adb + device facts (model, emulator flag, camera2 hardware level, ABI);
# I3 pushes the device-parity bundle (ml/runs/G9/stageI/device_parity) to /sdcard/Download/nscv_parity for the in-app parity screen;
# I4 records logcat lines tagged NSCV for -Minutes and summarises: per-stage ms (p50/p95), events, parity lines
#     ('NSCV parity file=p03.png maxdiff=0.004'), mapping lines ('NSCV map tap=..,.. frame=..,.. still=WxH crop=x,y,w,h rot=90 mirror=0').
# Emulator timings are functional only. No FPS figure is claimed from this script without a physical phone.
param([int]$Minutes = 3, [string]$Out = "g9i_device_log", [string]$Apk = "")
$ErrorActionPreference = "Stop"
Write-Host "== I1 unit + parity tests"
Push-Location native; npm test; if ($LASTEXITCODE -ne 0) { Write-Error "TS tests failed" }; Pop-Location
python -m pytest ml/eval/test_closeup.py ml/eval/test_verify.py ml/eval/test_camera_io.py ml/prices/tests -q; if ($LASTEXITCODE -ne 0) { Write-Error "Python tests failed" }
$adb = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adb) { Write-Warning "adb not found: install Android platform-tools; stopping after I1"; exit 0 }
$dev = (adb devices | Select-String "device$"); if (-not $dev) { Write-Warning "no device / emulator attached; stopping after I1"; exit 0 }
Write-Host "== I2 device facts"
$model = adb shell getprop ro.product.model; $emu = adb shell getprop ro.kernel.qemu; $abi = adb shell getprop ro.product.cpu.abi; $sdk = adb shell getprop ro.build.version.sdk
Write-Host "device: $model  abi: $abi  sdk: $sdk  emulator: $([bool]($emu -eq '1'))"
adb shell dumpsys media.camera | Select-String -Pattern "android.info.supportedHardwareLevel|Camera \d+ facing" | Select-Object -First 8
if ($emu -eq '1') { Write-Warning "EMULATOR: functional checks only; timings are NOT phone latency/FPS" }
if ($Apk -ne "") { adb install -r $Apk }
Write-Host "== I3 push device-parity bundle"
adb shell mkdir -p /sdcard/Download/nscv_parity
Get-ChildItem ml/runs/G9/stageI/device_parity | ForEach-Object { adb push $_.FullName /sdcard/Download/nscv_parity/ | Out-Null }
Write-Host "== I4 recording NSCV logcat for $Minutes min: run A1-A9 in docs/cv/gauntlet/G9_stageI_android_test.md"
adb logcat -c
$job = Start-Job -ScriptBlock { adb logcat -v epoch -s NSCV:* ReactNativeJS:* }
Start-Sleep -Seconds ($Minutes * 60); Stop-Job $job; $lines = Receive-Job $job; $lines | Set-Content "$Out.txt"
$rows = foreach ($l in $lines) { if ($l -match "NSCV.*stage=(\w+).*ms=([\d\.]+)") { [pscustomobject]@{ stage = $Matches[1]; ms = [double]$Matches[2] } } }
$rows | Export-Csv "$Out.csv" -NoTypeInformation
$rows | Group-Object stage | ForEach-Object { $v = $_.Group.ms | Sort-Object; $n = $v.Count
  if ($n -gt 0) { "{0,-10} n={1,5} p50={2,8:N1} ms p95={3,8:N1} ms" -f $_.Name, $n, $v[[int][math]::Floor(0.5 * ($n - 1))], $v[[int][math]::Floor(0.95 * ($n - 1))] } }
foreach ($l in $lines) { if ($l -match "event=(\w+)") { $Matches[1] } } | Group-Object | ForEach-Object { "event {0}: {1}" -f $_.Name, $_.Count }
$par = foreach ($l in $lines) { if ($l -match "NSCV parity file=(\S+) maxdiff=([\d\.]+)") { [pscustomobject]@{ f = $Matches[1]; d = [double]$Matches[2] } } }
if ($par) { $bad = $par | Where-Object { $_.d -gt 0.02 }; "parity: {0} files, {1} over 0.02" -f $par.Count, @($bad).Count } else { Write-Warning "no parity lines: run A3" }
($lines | Select-String "NSCV map ").Count | ForEach-Object { "mapping lines: $_ (A4/A5)" }
Write-Host "wrote $Out.txt / $Out.csv. Attach both, plus screenshots for A4-A8, to the Stage I device note."
