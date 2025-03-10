#!/bin/bash

# Script to clean up old files after confirming the new project structure works

echo "WARNING: This script will delete all files except for the 'projects' directory and essential files."
echo "Make sure you have tested the new project structure before running this script."
echo "Press Ctrl+C to cancel or Enter to continue..."
read

# Keep these files
KEEP_FILES=(
  "README.md"
  "deploy-projects.sh"
  "cleanup.sh"
  ".git"
  ".gitignore"
  "projects"
)

# Function to check if a file/directory should be kept
should_keep() {
  local file="$1"
  for keep in "${KEEP_FILES[@]}"; do
    if [[ "$file" == "$keep" ]]; then
      return 0
    fi
  done
  return 1
}

# List all files and directories in the current directory
for file in *; do
  if ! should_keep "$file"; then
    echo "Deleting: $file"
    rm -rf "$file"
  else
    echo "Keeping: $file"
  fi
done

echo "Cleanup complete!"
echo "The repository now contains only the new project structure in the 'projects' directory." 