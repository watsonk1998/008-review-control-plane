#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SUBMODULE_PATH = "external/hermes-agent"
EXPECTED_SUBMODULE_URL = "https://github.com/NousResearch/hermes-agent"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

REQUIRED_PATHS = [
    Path("AGENTS.md"),
    Path("external/README.md"),
    Path("external/hermes-agent"),
    Path("patches/hermes-agent"),
    Path("docs/architecture/hermes-upstream-contract.md"),
    Path("docs/architecture/plugin-system.md"),
    Path("docs/architecture/review-governance.md"),
    Path("config/hermes_upstream.yaml"),
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


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def verify_required_paths(errors: list[str]) -> None:
    for rel in REQUIRED_PATHS:
        if not path_exists(rel):
            errors.append(f"missing required path: {rel}")


def verify_gitmodules(errors: list[str]) -> None:
    gitmodules = REPO_ROOT / ".gitmodules"
    if not gitmodules.exists():
        errors.append("missing .gitmodules")
        return

    current_name: str | None = None
    submodules: dict[str, dict[str, str]] = {}
    for raw_line in gitmodules.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[submodule "):
            current_name = line.split('"')[1]
            submodules[current_name] = {}
            continue
        if "=" in line and current_name:
            key, value = [part.strip() for part in line.split("=", 1)]
            submodules[current_name][key] = value

    matched = None
    for data in submodules.values():
        if data.get("path") == EXPECTED_SUBMODULE_PATH:
            matched = data
            break

    if matched is None:
        errors.append(f".gitmodules does not declare path = {EXPECTED_SUBMODULE_PATH}")
        return

    if matched.get("url") != EXPECTED_SUBMODULE_URL:
        errors.append(
            f".gitmodules URL mismatch for {EXPECTED_SUBMODULE_PATH}: expected {EXPECTED_SUBMODULE_URL}, got {matched.get('url')!r}"
        )


def verify_submodule_semantics(errors: list[str]) -> None:
    ls_stage = run_git("ls-files", "--stage", EXPECTED_SUBMODULE_PATH)
    if ls_stage.returncode != 0:
        errors.append(f"git ls-files --stage failed for {EXPECTED_SUBMODULE_PATH}: {ls_stage.stderr.strip()}")
        return

    if "160000 " not in ls_stage.stdout:
        errors.append(f"{EXPECTED_SUBMODULE_PATH} is not recorded as a gitlink (mode 160000)")

    sub_status = run_git("submodule", "status", "--", EXPECTED_SUBMODULE_PATH)
    if sub_status.returncode != 0:
        errors.append(f"git submodule status failed for {EXPECTED_SUBMODULE_PATH}: {sub_status.stderr.strip()}")
    elif EXPECTED_SUBMODULE_PATH not in sub_status.stdout:
        errors.append(f"git submodule status did not report {EXPECTED_SUBMODULE_PATH}")

    gitdir_file = REPO_ROOT / EXPECTED_SUBMODULE_PATH / ".git"
    if not gitdir_file.exists():
        errors.append(f"missing {EXPECTED_SUBMODULE_PATH}/.git gitdir file")
    else:
        content = gitdir_file.read_text(encoding="utf-8").strip()
        if ".git/modules/" not in content:
            errors.append(f"{EXPECTED_SUBMODULE_PATH}/.git does not point into .git/modules/")


def verify_config(errors: list[str]) -> None:
    config_path = REPO_ROOT / "config/hermes_upstream.yaml"
    try:
        raw = config_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append("missing config/hermes_upstream.yaml")
        return

    mode_match = re.search(r'^\s*integration_mode:\s*"?(?P<mode>[A-Za-z0-9_\-]+)"?\s*$', raw, flags=re.M)
    pin_match = re.search(r'^\s*pinned_commit:\s*"?(?P<pin>[0-9a-f]{40})"?\s*$', raw, flags=re.M)

    if mode_match is None:
        errors.append("config/hermes_upstream.yaml missing integration_mode")
    elif mode_match.group("mode") != "submodule":
        errors.append(f'config/hermes_upstream.yaml integration_mode must be "submodule", got "{mode_match.group("mode")}"')

    if pin_match is None:
        errors.append("config/hermes_upstream.yaml missing valid pinned_commit")
        return

    pin = pin_match.group("pin")
    if not COMMIT_RE.match(pin):
        errors.append("config/hermes_upstream.yaml pinned_commit is not a valid 40-char sha")
        return

    head = run_git("-C", EXPECTED_SUBMODULE_PATH, "rev-parse", "HEAD")
    if head.returncode != 0:
        errors.append(f"unable to read submodule HEAD for {EXPECTED_SUBMODULE_PATH}: {head.stderr.strip()}")
        return

    actual_head = head.stdout.strip()
    if actual_head != pin:
        errors.append(
            f"config/hermes_upstream.yaml pinned_commit {pin} does not match submodule HEAD {actual_head}"
        )


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
    verify_gitmodules(errors)
    verify_submodule_semantics(errors)
    verify_config(errors)
    scan_python_files(errors)

    if errors:
        print("Hermes boundary verification: FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Hermes boundary verification: PASS")
    print("- submodule metadata present")
    print("- submodule semantics verified")
    print("- governance/config documents present")
    print("- no forbidden upstream import/path coupling detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
