#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SUBMODULE_PATH = "external/hermes-agent"
EXPECTED_SUBMODULE_URL = "https://github.com/NousResearch/hermes-agent"
EXPECTED_BRANCH = "main"
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
    if matched.get("branch") != EXPECTED_BRANCH:
        errors.append(
            f".gitmodules branch mismatch for {EXPECTED_SUBMODULE_PATH}: expected {EXPECTED_BRANCH}, got {matched.get('branch')!r}"
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
    repo_match = re.search(r'^\s*repo:\s*"?(?P<repo>https://github\.com/NousResearch/hermes-agent)"?\s*$', raw, flags=re.M)
    path_match = re.search(r'^\s*external_kernel_path:\s*"?(?P<path>external/hermes-agent)"?\s*$', raw, flags=re.M)
    submodule_path_match = re.search(r'^\s*submodule_path:\s*"?(?P<path>external/hermes-agent)"?\s*$', raw, flags=re.M)
    submodule_required_match = re.search(r'^\s*submodule_required:\s*(?P<value>true|false)\s*$', raw, flags=re.M)
    enforce_boundary_match = re.search(r'^\s*enforce_submodule_boundary:\s*(?P<value>true|false)\s*$', raw, flags=re.M)

    if mode_match is None:
        errors.append("config/hermes_upstream.yaml missing integration_mode")
    elif mode_match.group("mode") != "submodule":
        errors.append(f'config/hermes_upstream.yaml integration_mode must be "submodule", got "{mode_match.group("mode")}"')

    if repo_match is None:
        errors.append(f"config/hermes_upstream.yaml repo must match {EXPECTED_SUBMODULE_URL}")
    if path_match is None:
        errors.append(f"config/hermes_upstream.yaml external_kernel_path must match {EXPECTED_SUBMODULE_PATH}")
    if submodule_path_match is None:
        errors.append(f"config/hermes_upstream.yaml submodule_path must match {EXPECTED_SUBMODULE_PATH}")
    if submodule_required_match is None or submodule_required_match.group('value') != "true":
        errors.append("config/hermes_upstream.yaml submodule_required must be true")
    if enforce_boundary_match is None or enforce_boundary_match.group('value') != "true":
        errors.append("config/hermes_upstream.yaml enforce_submodule_boundary must be true")

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


def verify_readme(errors: list[str]) -> None:
    readme_path = REPO_ROOT / "external/README.md"
    text = readme_path.read_text(encoding="utf-8")

    forbidden_terms = [
        "planned_submodule",
        "Current mode in this checkout: planned_submodule",
    ]
    for term in forbidden_terms:
        if term in text:
            errors.append(f"external/README.md still contains deprecated planned-state wording: {term}")

    required_terms = [
        "Current mode in this checkout: **git submodule**",
        EXPECTED_SUBMODULE_URL,
        "Current pin: `af9caec44fdab7a1b883dede16fe1ce8c2d60fb9`",
        "make verify-hermes-boundary",
    ]
    for term in required_terms:
        if term not in text:
            errors.append(f"external/README.md missing required current-state text: {term}")


def verify_cross_file_consistency(errors: list[str]) -> None:
    readme_path = REPO_ROOT / "external/README.md"
    contract_path = REPO_ROOT / "docs/architecture/hermes-upstream-contract.md"
    config_path = REPO_ROOT / "config/hermes_upstream.yaml"
    
    if not (readme_path.exists() and contract_path.exists() and config_path.exists()):
        return # Missing files are caught by verify_required_paths

    readme_text = readme_path.read_text(encoding="utf-8")
    contract_text = contract_path.read_text(encoding="utf-8")
    
    # Very lightweight consistency mapping
    if EXPECTED_SUBMODULE_URL not in contract_text:
         errors.append("docs/architecture/hermes-upstream-contract.md missing correct upstream URL")
         
    if EXPECTED_BRANCH not in contract_text:
         errors.append("docs/architecture/hermes-upstream-contract.md missing correct tracking branch")
         
    # Ensure pin in readme matches contract roughly (if a pin is explicitly mentioned)
    match_readme = re.search(r'`([0-9a-f]{40})`', readme_text)
    match_contract = re.search(r'`([0-9a-f]{40})`', contract_text)
    
    if match_readme and match_contract:
        if match_readme.group(1) != match_contract.group(1):
             errors.append("Mismatch in pinned commit hashes between docs/architecture/...contract.md and external/README.md")

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


# ---------------------------------------------------------------------------
# Overlay boundary verification
# ---------------------------------------------------------------------------

OVERLAY_ROOT = Path("overlays/hermes-agent")
EXPECTED_OVERLAY_SUBDIRS = ("skills", "memory", "config", "prompts")


def verify_overlay_structure(errors: list[str]) -> None:
    """Verify that the overlay directory exists and has expected structure."""
    overlay_path = REPO_ROOT / OVERLAY_ROOT
    if not overlay_path.is_dir():
        errors.append(f"missing overlay root: {OVERLAY_ROOT}")
        return

    readme = overlay_path / "README.md"
    if not readme.is_file():
        errors.append(f"missing overlay README: {OVERLAY_ROOT}/README.md")

    for subdir in EXPECTED_OVERLAY_SUBDIRS:
        subdir_path = overlay_path / subdir
        if not subdir_path.is_dir():
            errors.append(f"missing overlay subdirectory: {OVERLAY_ROOT}/{subdir}/")


def verify_overlay_config_consistency(errors: list[str]) -> None:
    """Verify that config/hermes_upstream.yaml overlay_root matches actual directory."""
    config_path = REPO_ROOT / "config/hermes_upstream.yaml"
    if not config_path.exists():
        return  # Missing config caught elsewhere

    raw = config_path.read_text(encoding="utf-8")
    overlay_match = re.search(
        r'^\s*overlay_root:\s*"?(?P<path>[^"\s]+)"?\s*$', raw, flags=re.M
    )
    if overlay_match is None:
        errors.append("config/hermes_upstream.yaml missing overlay.overlay_root field")
        return

    declared_path = overlay_match.group("path")
    actual_path = REPO_ROOT / declared_path
    if not actual_path.is_dir():
        errors.append(
            f"config/hermes_upstream.yaml overlay_root '{declared_path}' "
            f"does not match an existing directory"
        )


# ---------------------------------------------------------------------------
# Smoke path isolation verification
# ---------------------------------------------------------------------------

SMOKE_SCRIPT_REL = "apps/api/scripts/run_local_hermes_smoke.py"
MINIMAL_REVIEW_SCRIPT_REL = "apps/api/scripts/run_local_hermes_minimal_review.py"

# Files that constitute the main runtime wiring — smoke must NOT be imported here
MAIN_CHAIN_FILES = [
    "apps/api/src/main_dependencies.py",
    "apps/api/src/orchestrator/deepresearch_runtime.py",
]

SMOKE_IMPORT_PATTERNS = [
    re.compile(r"run_local_hermes_smoke"),
    re.compile(r"run_local_hermes_minimal_review"),
    re.compile(r"hermes_local_kernel_adapter", re.IGNORECASE),
    re.compile(r"HermesLocalKernelAdapter"),
    re.compile(r"HermesKernelLauncher"),
]


def verify_smoke_path_isolation(errors: list[str]) -> None:
    """Verify that smoke path components are not imported by the main chain."""
    for rel_path in MAIN_CHAIN_FILES:
        path = REPO_ROOT / rel_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern in SMOKE_IMPORT_PATTERNS:
                if pattern.search(line):
                    errors.append(
                        f"{rel_path}:{lineno}: smoke path component "
                        f"leaked into main chain: {line.strip()}"
                    )


def verify_local_kernel_non_default(errors: list[str]) -> None:
    """Verify that HermesLocalKernelAdapter is still non-default / not enabled."""
    config_path = REPO_ROOT / "config/hermes_upstream.yaml"
    if not config_path.exists():
        return

    raw = config_path.read_text(encoding="utf-8")

    # Check runtime_kernel_mode
    mode_match = re.search(
        r'^\s*runtime_kernel_mode:\s*"?(?P<mode>[^"\s]+)"?\s*$', raw, flags=re.M
    )
    if mode_match and mode_match.group("mode") not in (
        "local_kernel_available_not_enabled",
        "external_only",
    ):
        errors.append(
            f"config/hermes_upstream.yaml runtime_kernel_mode is "
            f"'{mode_match.group('mode')}' — expected 'local_kernel_available_not_enabled'"
        )

    # Check adapter_status
    status_match = re.search(
        r'^\s*adapter_status:\s*"?(?P<status>[^"\s]+)"?\s*$', raw, flags=re.M
    )
    if status_match and status_match.group("status") not in (
        "non_default_smoke_only",
        "non_default_minimal_execution_available",
        "skeleton",
        "disabled",
    ):
        errors.append(
            f"config/hermes_upstream.yaml adapter_status is "
            f"'{status_match.group('status')}' — local kernel should not be enabled"
        )


def main() -> int:
    errors: list[str] = []
    verify_required_paths(errors)
    verify_gitmodules(errors)
    verify_submodule_semantics(errors)
    verify_config(errors)
    verify_readme(errors)
    verify_cross_file_consistency(errors)
    scan_python_files(errors)
    verify_overlay_structure(errors)
    verify_overlay_config_consistency(errors)
    verify_smoke_path_isolation(errors)
    verify_local_kernel_non_default(errors)

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
    print("- overlay structure verified")
    print("- local kernel path isolation verified")
    print("- local kernel non-default status confirmed")
    print("- minimal execution available, but not wired into production")
    return 0


if __name__ == "__main__":
    sys.exit(main())

