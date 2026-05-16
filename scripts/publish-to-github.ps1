param(
    [string]$RepoName = (Split-Path -Leaf (Get-Location)),
    [string]$RemoteUrl = "",
    [string]$Branch = "main",
    [ValidateSet("public", "private", "internal")]
    [string]$Visibility = "private",
    [string]$CommitMessage = "Initial commit",
    [switch]$ReplaceRemoteContent
)

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
$git = Find-Tool "git" @(
    (Join-Path $toolRoot "mingit\cmd\git.exe"),
    "C:\Program Files\Git\cmd\git.exe"
)
$gh = Find-Tool "gh" @(
    (Join-Path $toolRoot "gh\gh.exe"),
    "C:\Program Files\GitHub CLI\gh.exe"
)

if (-not (Test-Path ".git")) {
    & $git init -b $Branch
}

$name = & $git config user.name
$email = & $git config user.email
if (-not $name) {
    $name = Read-Host "Git user.name"
    & $git config user.name $name
}
if (-not $email) {
    $email = Read-Host "Git user.email"
    & $git config user.email $email
}

& $gh auth status 1>$null

$remote = & $git remote get-url origin 2>$null
if (-not $remote) {
    if ($RemoteUrl) {
        & $git remote add origin $RemoteUrl
    } else {
        & $git add -A
        $pending = & $git status --porcelain
        if ($pending) {
            & $git commit -m $CommitMessage
        }
        & $gh repo create $RepoName "--$Visibility" --source . --remote origin --push
        Write-Host "Done. Repository is ready on GitHub."
        exit 0
    }
} else {
    if ($RemoteUrl -and ($remote -ne $RemoteUrl)) {
        & $git remote set-url origin $RemoteUrl
    }
}

$remoteBranchExists = $false
& $git ls-remote --exit-code --heads origin $Branch 1>$null 2>$null
if ($LASTEXITCODE -eq 0) {
    $remoteBranchExists = $true
}

$hasHead = $true
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $git rev-parse --verify HEAD 1>$null 2>$null
$headExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference
if ($headExitCode -ne 0) {
    $hasHead = $false
}

if ($remoteBranchExists -and -not $hasHead) {
    if (-not $ReplaceRemoteContent) {
        throw "Remote branch '$Branch' already has files. Re-run with -ReplaceRemoteContent to keep its history but replace the latest tree with this local project."
    }

    & $git fetch origin $Branch
    & $git add -A
    $tree = & $git write-tree
    $parent = & $git rev-parse "origin/$Branch"
    $commit = & $git commit-tree $tree -p $parent -m $CommitMessage
    & $git update-ref "refs/heads/$Branch" $commit
    & $git push -u origin $Branch
    if ($LASTEXITCODE -ne 0) {
        throw "Push failed. Review the GitHub error above, fix the issue, then run this script again."
    }
    Write-Host "Done. Remote history was preserved and latest content now matches this local project."
    exit 0
}

& $git add -A
$pending = & $git status --porcelain
if ($pending) {
    & $git commit -m $CommitMessage
}

& $git push -u origin $Branch
if ($LASTEXITCODE -ne 0) {
    throw "Push failed. Review the GitHub error above, fix the issue, then run this script again."
}

Write-Host "Done. Repository is ready on GitHub."
