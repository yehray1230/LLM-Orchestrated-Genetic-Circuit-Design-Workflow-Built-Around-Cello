$ErrorActionPreference = "Stop"

function Find-Tool {
    param(
        [string]$Name,
        [string[]]$Fallbacks
    )

    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    foreach ($path in $Fallbacks) {
        if (Test-Path $path) {
            return $path
        }
    }

    throw "Could not find $Name. Open a new terminal, or install the Git/GitHub CLI tools first."
}

$toolRoot = Join-Path $env:LOCALAPPDATA "Programs\codex-github-tools"
$gh = Find-Tool "gh" @(
    (Join-Path $toolRoot "gh\gh.exe"),
    "C:\Program Files\GitHub CLI\gh.exe"
)

& $gh auth login --hostname github.com --git-protocol https --web
& $gh auth setup-git
& $gh auth status
