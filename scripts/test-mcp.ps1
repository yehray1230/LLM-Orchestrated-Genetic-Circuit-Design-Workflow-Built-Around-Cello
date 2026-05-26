param(
    [switch]$All,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[mcp-test] $Message"
}

try {
    $pythonCommand = Get-Command $Python -ErrorAction Stop
} catch {
    Write-Error "Python executable '$Python' was not found. Install Python or pass -Python <path-to-python>."
    exit 1
}

Write-Step "Using Python: $($pythonCommand.Source)"

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $Python -c "import pytest" 2>$null
$pytestImportExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference

if ($pytestImportExitCode -ne 0) {
    Write-Error "pytest is not installed. Run: pip install -r requirements-dev.txt"
    exit 1
}

$ErrorActionPreference = "Continue"
if ($All) {
    Write-Step "Running full test suite"
    & $Python -m pytest
} else {
    Write-Step "Running MCP focused tests"
    & $Python -m pytest tests/test_mcp_server.py
}

exit $LASTEXITCODE
