[CmdletBinding()]
param(
    [string]$Destination,
    [string]$ArchivePath,
    [string]$DownloadUrl = "https://github.com/Genymobile/scrcpy/releases/download/v4.1/scrcpy-win64-v4.1.zip",
    [string]$ExpectedSha256 = "5b12172b3264b2889f4583ee64752ce832e29bc8b1089dca81093459697165db",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Destination) {
    $Destination = Join-Path $projectRoot "vendor\scrcpy"
}
$destinationPath = [IO.Path]::GetFullPath($Destination)

if ((Test-Path (Join-Path $destinationPath "scrcpy.exe")) -and
    (Test-Path (Join-Path $destinationPath "adb.exe")) -and
    -not $Force) {
    Write-Host "scrcpy is already installed at $destinationPath"
    return
}

$scratch = Join-Path ([IO.Path]::GetTempPath()) ("scrcpy-gui-" + [guid]::NewGuid().ToString("N"))
$downloadedArchive = Join-Path $scratch "scrcpy.zip"
$extractRoot = Join-Path $scratch "extract"

try {
    New-Item -ItemType Directory -Path $scratch, $extractRoot -Force | Out-Null
    if ($ArchivePath) {
        $archive = [IO.Path]::GetFullPath($ArchivePath)
        if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
            throw "Archive not found: $archive"
        }
    }
    else {
        Write-Host "Downloading official scrcpy v4.1..."
        Invoke-WebRequest -Uri $DownloadUrl -OutFile $downloadedArchive -UseBasicParsing
        $archive = $downloadedArchive
    }

    $actualSha256 = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualSha256 -ne $ExpectedSha256.ToLowerInvariant()) {
        throw "SHA-256 mismatch. Expected $ExpectedSha256, got $actualSha256"
    }

    Expand-Archive -LiteralPath $archive -DestinationPath $extractRoot -Force
    $scrcpyExe = Get-ChildItem -LiteralPath $extractRoot -Filter "scrcpy.exe" -File -Recurse | Select-Object -First 1
    if (-not $scrcpyExe) {
        throw "The verified archive does not contain scrcpy.exe"
    }
    $sourceDirectory = $scrcpyExe.Directory.FullName
    if (-not (Test-Path (Join-Path $sourceDirectory "adb.exe"))) {
        throw "The verified archive does not contain adb.exe next to scrcpy.exe"
    }

    $destinationParent = Split-Path -Parent $destinationPath
    New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
    if (Test-Path -LiteralPath $destinationPath) {
        Remove-Item -LiteralPath $destinationPath -Recurse -Force
    }
    Copy-Item -LiteralPath $sourceDirectory -Destination $destinationPath -Recurse
    Set-Content -LiteralPath (Join-Path $destinationPath ".scrcpy-version") -Value "v4.1" -Encoding ascii
    Write-Host "Installed verified scrcpy v4.1 at $destinationPath"
}
finally {
    if (Test-Path -LiteralPath $scratch) {
        Remove-Item -LiteralPath $scratch -Recurse -Force
    }
}
