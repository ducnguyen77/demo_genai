
param(
    [Parameter(Mandatory = $true)]
    [string]$Message
)

$ErrorActionPreference = "Stop"

# ==========================================
# Git helper function
# ==========================================
function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$GitArgs
    )

    & git @GitArgs

    if ($LASTEXITCODE -ne 0) {
        throw "Git command failed: git $($GitArgs -join ' ')"
    }
}

# ==========================================
# Navigate to repository root
# ==========================================
$repoRoot = & git -C $PSScriptRoot rev-parse --show-toplevel

if ($LASTEXITCODE -ne 0) {
    throw "Not inside a Git repository."
}

Set-Location $repoRoot

Write-Host "Repository: $repoRoot"

# ==========================================
# Verify branch
# ==========================================
$branch = & git branch --show-current

if ($branch -ne "dev") {
    throw "You are on '$branch', not 'dev'."
}

Write-Host "Current branch: $branch"

# ==========================================
# Stage changes
# ==========================================
Write-Host "Staging changes..."

Invoke-Git -GitArgs @("add", "-A")

# ==========================================
# Check staged changes
# ==========================================
& git diff --cached --quiet
$diffExitCode = $LASTEXITCODE

if ($diffExitCode -eq 0) {
    Write-Host "No new changes to commit."
}
elseif ($diffExitCode -eq 1) {

    Write-Host "Creating commit..."

    Invoke-Git -GitArgs @(
        "commit",
        "-m",
        $Message
    )
}
else {
    throw "Unable to check staged changes."
}

# ==========================================
# Push to remote
# ==========================================
Write-Host "Pushing to GitHub..."

Invoke-Git -GitArgs @(
    "push",
    "-u",
    "origin",
    "dev"
)

Write-Host "Push completed successfully."

# ==========================================
# Verify synchronization
# ==========================================
Invoke-Git -GitArgs @("status", "-sb")
Invoke-Git -GitArgs @("log", "-1", "--oneline")
