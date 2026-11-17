# To commit changes to the NLP project, run this script in PowerShell. It will stage all changes, commit them with a message, and push to the remote dev branch.

# Stop if a command fails
$ErrorActionPreference = "Stop"

# Navigate to the repository root
Set-Location (git rev-parse --show-toplevel)

# Check current branch
git branch --show-current

# Stage changes
git add .

# Commit changes
git commit -m "Adding project.toml"

# Push to remote dev branch
git push origin dev
