# G9 Stage G device / emulator check for the user's Windows PC. NOT run in the sandbox (no adb, no SDK, no KVM).
# Usage (PowerShell, repo root):  powershell -ExecutionPolicy Bypass -File native/scripts/g9g-device-check.ps1 [-Minutes 3]
# 1) runs the TS + Python close-up tests; 2) checks adb and the attached device/emulator; 3) clears logcat and records lines
# tagged NSCV (the frame processor should log: NSCV stage=<detect|track|crop|condition|measure|ripeness|rules|gate|price> ms=<x>
# event=<identified|graded|not_graded|unable> reason=<...>) for -Minutes, then writes a CSV and p50/p95 per stage.
# FPS from an emulator is function-only; only a physical phone gives a latency/FPS number.
param([int]$Minutes = 3, [string]$Out = "g9g_device_log")
$ErrorActionPreference = "Stop"
Write-Host "== D1 unit + parity tests"
Push-Location native; npm test; if ($LASTEXITCODE -ne 0) { Write-Error "TS tests failed" }; Pop-Location
python -m pytest ml/eval/test_closeup.py ml/prices/tests -q; if ($LASTEXITCODE -ne 0) { Write-Error "Python tests failed" }
Write-Host "== adb / device"
$adb = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adb) { Write-Warning "adb not found: install Android platform-tools; stopping after D1"; exit 0 }
$dev = (adb devices | Select-String "device$")
if (-not $dev) { Write-Warning "no device or emulator attached; stopping after D1"; exit 0 }
$model = adb shell getprop ro.product.model; $emu = adb shell getprop ro.kernel.qemu
Write-Host "device: $model  emulator: $([bool]($emu -eq '1'))"
if ($emu -eq '1') { Write-Warning "EMULATOR: functional checks only, timings are NOT phone FPS" }
Write-Host "== recording NSCV logcat for $Minutes min: open the Scan screen and run D2-D8 from docs/cv/gauntlet/G9_stageG_device_test.md"
adb logcat -c
$job = Start-Job -ScriptBlock { param($m) adb logcat -v epoch -s NSCV:* ReactNativeJS:* | ForEach-Object { $_ } } -ArgumentList $Minutes
Start-Sleep -Seconds ($Minutes * 60); Stop-Job $job; $lines = Receive-Job $job
$lines | Set-Content "$Out.txt"
$rows = foreach ($l in $lines) {
  if ($l -match "NSCV.*stage=(\w+).*ms=([\d\.]+)") { [pscustomobject]@{ stage = $Matches[1]; ms = [double]$Matches[2] } }
}
$rows | Export-Csv "$Out.csv" -NoTypeInformation
$rows | Group-Object stage | ForEach-Object {
  $v = $_.Group.ms | Sort-Object; $n = $v.Count
  if ($n -gt 0) { "{0,-10} n={1,5} p50={2,8:N1} ms p95={3,8:N1} ms" -f $_.Name, $n, $v[[int][math]::Floor(0.5 * ($n - 1))], $v[[int][math]::Floor(0.95 * ($n - 1))] }
}
$ev = foreach ($l in $lines) { if ($l -match "event=(\w+)") { $Matches[1] } }
$ev | Group-Object | ForEach-Object { "event {0}: {1}" -f $_.Name, $_.Count }
Write-Host "wrote $Out.txt / $Out.csv. Attach both to the G9 Stage G device-validation note."
