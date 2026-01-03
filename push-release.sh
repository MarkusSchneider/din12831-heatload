#!/bin/bash
# Script to trigger a release build by creating and pushing a git tag

set -e  # Exit on error

# Check if tag name is provided
if [ -z "$1" ]; then
    echo "❌ Error: No tag name provided"
    echo ""
    echo "Usage: ./release.sh <tag-name>"
    echo "Example: ./release.sh v1.0.0"
    exit 1
fi

TAG_NAME="$1"

# Validate tag format (should start with 'v')
if [[ ! "$TAG_NAME" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "⚠️  Warning: Tag name should follow semantic versioning (e.g., v1.0.0)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted"
        exit 1
    fi
fi

# Check if tag already exists locally
if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo "❌ Error: Tag '$TAG_NAME' already exists locally"
    echo "   Use 'git tag -d $TAG_NAME' to delete it first"
    exit 1
fi

# Check if tag already exists on remote
if git ls-remote --tags origin | grep -q "refs/tags/$TAG_NAME$"; then
    echo "❌ Error: Tag '$TAG_NAME' already exists on remote"
    exit 1
fi

# Show current status
echo "📋 Current status:"
echo "   Branch: $(git branch --show-current)"
echo "   Commit: $(git rev-parse --short HEAD)"
echo ""

# Confirm with user
echo "🏷️  Creating release tag: $TAG_NAME"
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted"
    exit 1
fi

# Create annotated tag
echo ""
echo "🏷️  Creating tag..."
git tag -a "$TAG_NAME" -m "Release $TAG_NAME"

# Push tag to remote
echo "📤 Pushing tag to remote..."
git push origin "$TAG_NAME"

echo ""
echo "✅ Success! Release build triggered for $TAG_NAME"
echo ""
echo "🔗 Check the build progress at:"
echo "   https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
echo ""
echo "📦 The release will be available at:"
echo "   https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/releases/tag/$TAG_NAME"
