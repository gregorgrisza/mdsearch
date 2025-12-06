#!/bin/bash

# set -x

[[ "$#" -lt 1  ]] && echo -e "Usage: \n\t $0 <markdown_source_directory>\n" && exit 1

CDIR="$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)"
TARGET_DIR="${CDIR}/docs"
MD_SOURCES="${1}"
[[ ! -d "${MD_SOURCES}" ]] && echo "Required valid directory parameter! Leaving..." && exit 1
[[ "$(find ${TARGET_DIR} -mindepth 1 -print)" ]] && echo "Destination directory ${TARGET_DIR} is not empty! Leaving..." && exit 1

LIST_FILE=$(mktemp)
find "${MD_SOURCES}" -type f -name "*.md" -not -path "${TARGET_DIR}" > ${LIST_FILE}

cat $LIST_FILE

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

rm -fr ${LIST_FILE}