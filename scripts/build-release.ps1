[CmdletBinding()]
param(
    [string]$Version = "0.1.0",
    [switch]$SkipDownload
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$vendorRoot = Join-Path $projectRoot "vendor\scrcpy"
$buildRoot = Join-Path $projectRoot "build"
$appDist = Join-Path $buildRoot "app"
$stageRoot = Join-Path $buildRoot "release\scrcpy-gui-v$Version-windows-x64"
$archivePath = Join-Path $buildRoot "scrcpy-gui-v$Version-windows-x64.zip"

if (-not $SkipDownload) {
    & (Join-Path $PSScriptRoot "setup-scrcpy.ps1")
}
if (-not (Test-Path (Join-Path $vendorRoot "scrcpy.exe"))) {
    throw "scrcpy is not installed. Run scripts/setup-scrcpy.ps1 first."
}

if (Test-Path -LiteralPath $buildRoot) {
    Remove-Item -LiteralPath $buildRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $appDist, $stageRoot -Force | Out-Null

Push-Location $projectRoot
try {
    python -m PyInstaller main.py --onefile --windowed --name scrcpy-gui --noconfirm --clean `
        --distpath $appDist --workpath (Join-Path $buildRoot "pyinstaller") --specpath $buildRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}

Copy-Item -LiteralPath (Join-Path $appDist "scrcpy-gui.exe") -Destination $stageRoot
Copy-Item -Path (Join-Path $vendorRoot "*") -Destination $stageRoot -Recurse

$licenseRoot = Join-Path $stageRoot "licenses"
New-Item -ItemType Directory -Path $licenseRoot -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot "LICENSE") -Destination (Join-Path $licenseRoot "scrcpy-gui-LICENSE.txt")
Copy-Item -LiteralPath (Join-Path $projectRoot "THIRD_PARTY_NOTICES.md") -Destination $stageRoot
$scrcpyLicense = @("LICENSE", "LICENSE.txt") |
    ForEach-Object { Join-Path $vendorRoot $_ } |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1
if ($scrcpyLicense) {
    Copy-Item -LiteralPath $scrcpyLicense -Destination (Join-Path $licenseRoot "scrcpy-LICENSE.txt")
}
else {
    throw "The scrcpy distribution does not contain a license file"
}

@"
scrcpy-gui v$Version

Run scrcpy-gui.exe. This package includes the official scrcpy v4.1 Windows x64
distribution. See THIRD_PARTY_NOTICES.md and licenses/ for licensing details.
"@ | Set-Content -LiteralPath (Join-Path $stageRoot "README.txt") -Encoding utf8

Compress-Archive -Path $stageRoot -DestinationPath $archivePath -CompressionLevel Optimal -Force
$hash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$archivePath.sha256" -Value "$hash  $([IO.Path]::GetFileName($archivePath))" -Encoding ascii
Write-Host "Built $archivePath"
Write-Host "SHA-256 $hash"
