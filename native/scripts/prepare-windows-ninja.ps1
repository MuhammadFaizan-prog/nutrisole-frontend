$ErrorActionPreference = 'Stop'
$taskToolDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../.tools/ninja/1.13.2'))
$taskNinjaExe = Join-Path $taskToolDir 'ninja.exe'
if (Test-Path -LiteralPath $taskNinjaExe) {
    & $taskNinjaExe --version
    exit $LASTEXITCODE
}
New-Item -ItemType Directory -Path $taskToolDir -Force | Out-Null
$taskToolZip = Join-Path $taskToolDir 'ninja-win.zip'
Invoke-WebRequest -Uri 'https://github.com/ninja-build/ninja/releases/download/v1.13.2/ninja-win.zip' -OutFile $taskToolZip
$taskExpectedHash = '07fc8261b42b20e71d1720b39068c2e14ffcee6396b76fb7a795fb460b78dc65'
if ((Get-FileHash -LiteralPath $taskToolZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskExpectedHash) {
    throw 'The downloaded Ninja archive failed its SHA256 check.'
}
Expand-Archive -LiteralPath $taskToolZip -DestinationPath $taskToolDir -Force
& $taskNinjaExe --version
exit $LASTEXITCODE
