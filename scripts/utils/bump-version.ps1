# Script to increment version before push
# Usage: .\scripts\bump-version.ps1

$VERSION_FILE = "VERSION"
$CURRENT_VERSION = Get-Content $VERSION_FILE -ErrorAction SilentlyContinue

if (-not $CURRENT_VERSION) {
    $CURRENT_VERSION = "1.0.0"
    Set-Content $VERSION_FILE $CURRENT_VERSION
}

# Parse version (format: MAJOR.MINOR.PATCH)
$parts = $CURRENT_VERSION.Trim().Split('.')
$MAJOR = [int]$parts[0]
$MINOR = [int]$parts[1]
$PATCH = [int]$parts[2]

# Increment PATCH version
$PATCH++
$NEW_VERSION = "$MAJOR.$MINOR.$PATCH"

# Update version file
Set-Content $VERSION_FILE $NEW_VERSION

# Add version file to staging
git add $VERSION_FILE

# Create a commit for version bump
git commit -m "chore: bump version to $NEW_VERSION" --no-verify

Write-Host "Version incremented: $CURRENT_VERSION -> $NEW_VERSION" -ForegroundColor Green

exit 0


