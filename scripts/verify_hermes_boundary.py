#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    Path("AGENTS.md"),
    Path("external/README.md"),
    Path("patches/hermes-agent"),
    Path("docs/architecture/hermes-upstream-contract.md"),
    Path("docs/architecture/plugin-system.md"),
    Path("docs/architecture/review-governance.md"),
    Path("config/hermes_upstream.yaml"),
]

FALLBACK_MARKERS = [
    Path("external/hermes-agent"),
    Path("external/README.md"),
]

ALLOWLIST = {
    "apps/api/src/review/hermes_review_engine.py",
}

FORBIDDEN_PATTERNS = [
    re.compile(r"^\s*from\s+agent(?:\.|\s+import\b)"),
    re.compile(r"^\s*import\s+agent(?:\.|\b)"),
    re.compile(r"^\s*from\s+gateway(?:\.|\s+import\b)"),
    re.compile(r"^\s*import\s+gateway(?:\.|\b)"),
    re.compile(r"^\s*from\s+model_tools\s+import\b"),
    re.compile(r"^\s*import\s+model_tools\b"),
    re.compile(r"^\s*from\s+run_agent\s+import\b"),
    re.compile(r"^\s*import\s+run_agent\b"),
]

SYS_PATH_PATTERN = re.compile(r"sys\.path\.(?:append|insert)\((?P<arg>.+)\)")
SUBPROCESS_PATTERN = re.compile(r"(subprocess\.(?:run|Popen)|cwd\s*=)")


def path_exists(path: Path) -> bool:
    return (REPO_ROOT / path).exists()


def verify_required_paths(errors: list[str]) -> None:
    for rel in REQUIRED_PATHS:
        if not path_exists(rel):
            errors.append(f"missing required path: {rel}")


def verify_external_boundary(errors: list[str]) -> None:
    if not any(path_exists(marker) for marker in FALLBACK_MARKERS):
        errors.append("missing external Hermes boundary: expected external/hermes-agent or documented fallback markers")


def scan_python_files(errors: list[str]) -> None:
    src_root = REPO_ROOT / "apps/api/src"
    if not src_root.exists():
        errors.append("missing apps/api/src")
        return

    for path in src_root.rglob("*.py"):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    errors.append(f"{rel}:{lineno}: forbidden upstream import coupling: {line.strip()}")

            if "external/hermes-agent" in line and SYS_PATH_PATTERN.search(line):
                errors.append(f"{rel}:{lineno}: forbidden sys.path coupling to external/hermes-agent")

            if "external/hermes-agent" in line and SUBPROCESS_PATTERN.search(line):
                errors.append(f"{rel}:{lineno}: forbidden subprocess/cwd coupling to external/hermes-agent")


def main() -> int:
    errors: list[str] = []
    verify_required_paths(errors)
    verify_external_boundary(errors)
    scan_python_files(errors)

    if errors:
        print("Hermes boundary verification: FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Hermes boundary verification: PASS")
    print("- external boundary markers present")
    print("- governance/config documents present")
    print("- no forbidden upstream import/path coupling detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
