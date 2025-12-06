#!/bin/bash

set -x

LIST_FILE="$HOME/listOfMDFiles.txt"
TARGET_DIR="${1:-$PWD/docs}"

while IFS= read -r filepath; do
    # Skip empty lines
    [ -z "$filepath" ] && continue

    # Remove home directory prefix
    relative_path="${filepath#$HOME/}"

    # Determine destination file path
    cdir=$(dirname $relative_path)
    cfile=$(basename $relative_path)
    dest_dir="$TARGET_DIR/${cdir//./_}"

    # Create directory structure
    mkdir -p "$dest_dir"

    # Copy the file
    cp "$filepath" "$dest_dir/$cfile"

    echo "Copied: $filepath -> $dest_dir/$cfile"
done < "$LIST_FILE"
