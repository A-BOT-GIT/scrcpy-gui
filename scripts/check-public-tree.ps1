$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $tracked = @(git ls-files)
    if ($LASTEXITCODE -ne 0) { throw "Unable to read tracked files" }

    $forbiddenPaths = @(
        "docs/PROJECT_IMPLEMENTATION_PLAN.md",
        "docs/PROJECT_WORK_SUMMARY.md",
        ".agents/",
        ".codex/"
    )
    foreach ($path in $tracked) {
        foreach ($forbidden in $forbiddenPaths) {
            if ($path.StartsWith($forbidden, [StringComparison]::OrdinalIgnoreCase)) {
                throw "Forbidden tracked path: $path"
            }
        }
    }

    $patterns = @(
        "[A-Za-z]:\\Users\\[^\\]+",
        "[A-Za-z]:\\[^\r\n]*scrcpy-win64",
        "(?i)[A-Z0-9._%+-]+@(gmail|qq|163)\\.com",
        "(?i)A-BOT-GIT/scrcpy-win64-gui"
    )
    foreach ($path in $tracked) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { continue }
        $content = Get-Content -LiteralPath $path -Raw -ErrorAction SilentlyContinue
        foreach ($pattern in $patterns) {
            if ($path -eq "scripts/check-public-tree.ps1") { continue }
            if ($content -match $pattern) {
                throw "Private or legacy value found in ${path}: $pattern"
            }
        }
    }
    Write-Host "Public tree check passed for $($tracked.Count) tracked files."
}
finally {
    Pop-Location
}
