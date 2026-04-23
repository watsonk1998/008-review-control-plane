    #!/usr/bin/env bash
    set -euo pipefail

    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    INTEGRATION_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
    REPO_ROOT="$(cd "$INTEGRATION_ROOT/../.." && pwd)"
    ARTIFACT_DIR="$REPO_ROOT/artifacts/fastgpt"
    TOOLSET_SRC="$INTEGRATION_ROOT/toolset/hermesStructuredReview"
    WORKDIR="${TMPDIR:-/tmp}/fastgpt-plugin-hermes-build"

    mkdir -p "$ARTIFACT_DIR"

    if ! command -v bun >/dev/null 2>&1; then
      echo "bun is required for official .pkg builds. Install bun first." >&2
      exit 1
    fi

    rm -rf "$WORKDIR"
    git clone --depth 1 https://github.com/labring/fastgpt-plugin "$WORKDIR"
    rm -rf "$WORKDIR/modules/tool/packages/hermesStructuredReview"
    mkdir -p "$WORKDIR/modules/tool/packages"
    cp -R "$TOOLSET_SRC" "$WORKDIR/modules/tool/packages/hermesStructuredReview"

    pushd "$WORKDIR" >/dev/null
    bun install
    bun run build:pkg
    popd >/dev/null

    PKG_FILE=$(find "$WORKDIR/dist/pkgs" -maxdepth 1 -type f -name '*.pkg' | head -n 1 || true)
    if [[ -z "$PKG_FILE" ]]; then
      echo "No .pkg file produced by fastgpt-plugin build" >&2
      exit 1
    fi

    cp "$PKG_FILE" "$ARTIFACT_DIR/"
    python3 - "$ARTIFACT_DIR/$(basename "$PKG_FILE")" <<'PY2'
from pathlib import Path
import sys
path = Path(sys.argv[1])
size_mb = path.stat().st_size / (1024 * 1024)
print(f'pkg: {path}')
print(f'size_mb: {size_mb:.2f}')
if size_mb >= 100:
    raise SystemExit('Package exceeds 100MB upload limit')
PY2
