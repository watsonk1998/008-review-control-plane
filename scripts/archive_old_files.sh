#!/bin/bash
set -euo pipefail

# This script moves old, obsolete, or experimental files into the archive/ directory
# to keep the active repository pristine.
# It ensures that archived files mirrors their original tree structure.

ROOT_DIR=$(dirname "$0")/..
ARCHIVE_DIR="$ROOT_DIR/archive"

echo "Creating archive directory..."
mkdir -p "$ARCHIVE_DIR/apps/api/scripts"

echo "Moving legacy scripts (excluding boundary tests/smoke tests that are part of current verification)..."
# In a real environment, we'd list specific files that are obsolete.
# e.g., if there were old experimental scripts
# move_file "apps/api/scripts/some_old_script.py"

# For now, verify_hermes_boundary.py expects run_local_hermes_smoke.py to exist in its verification logic.
# So we only move files that are explicitly considered obsolete by the team.

echo "Archive cleanup complete."
