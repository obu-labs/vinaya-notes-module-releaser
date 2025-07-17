#!/bin/bash

cd "$1"
if latest_tag=$(gh release view --json tagName -q .tagName 2>/dev/null); then
  echo "Got release"
else
  echo "No release found"
  tag=""
fi
echo "Latest release was: ${latest_tag:-"(none)"}"

# Handle first version (no previous tag)
if [ -z "$latest_tag" ]; then
    next_version="1.0.0"
    cd "$GITHUB_WORKSPACE"
else
    # Download the previous release
    mkdir "$MY_WORKING_DIR/previousrelease"
    gh release download "$latest_tag" --dir "$MY_WORKING_DIR/previousrelease"
    cd "$MY_WORKING_DIR/previousrelease"
    [ $(ls -1 *.zip 2>/dev/null | wc -l) -eq 1 ] || { echo "Error: Directory must contain exactly one .zip file" >&2; exit 1; }
    unzip -q *.zip -d ../previous
    cd ..

    # Extract and validate version components
    version_part="${latest_tag#v}"
    IFS='.' read -r major minor patch <<< "$version_part"
    
    if ! [[ "$major" =~ ^[0-9]+$ ]] || ! [[ "$minor" =~ ^[0-9]+$ ]] || ! [[ "$patch" =~ ^[0-9]+$ ]]; then
        echo "Error: Invalid version format in latest_tag: $latest_tag" >&2
        exit 1
    fi

    # Create temporary files for directory listings
    prev_list=$(mktemp)
    latest_list=$(mktemp)
    
    # Generate file lists (non-hidden files only)
    (cd previous && find . -type f ! -path '*/.*' ! -name '.*' | sort) > "$prev_list"
    cd "$GITHUB_WORKSPACE"
    (cd "$1" && find . -type f ! -path '*/.*' ! -name '.*' | sort) > "$latest_list"

    # Check for files removed from latest
    if read -r _ < <(comm -23 "$prev_list" "$latest_list"); then
        echo "INFO: Found file(s) removed in the latest. Bumping the major version number."
        # Major bump: file(s) removed
        major=$((major + 1))
        minor=0
        patch=0
    # Check for new files in latest
    elif read -r _ < <(comm -13 "$prev_list" "$latest_list"); then
        echo "INFO: Found file(s) added to the latest. Bumping the minor version number."
        # Minor bump: new file(s) added
        minor=$((minor + 1))
        patch=0
    else
        # Patch bump: only modifications
        patch=$((patch + 1))
    fi

    # Cleanup temp files
    rm -f "$prev_list" "$latest_list"
    
    next_version="$major.$minor.$patch"
fi

echo "Next version: $next_version"
echo "version=$next_version" >> $GITHUB_OUTPUT
# Package up the release
cd "$1"
zip --quiet -r "$GITHUB_WORKSPACE/content.zip" . -x \*.yaml -x '.*' -x '*/.*'