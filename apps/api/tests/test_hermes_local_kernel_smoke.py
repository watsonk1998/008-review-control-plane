"""
Lightweight tests for the local kernel smoke path.

These tests verify:
1. HermesKernelLauncher dry-run and smoke modes
2. HermesLocalKernelAdapter smoke exercise
3. Overlay root resolution
4. Non-default / isolation invariants

These tests do NOT:
- Start a real kernel subprocess
- Depend on external/hermes-agent being fully initialized
- Touch the production runtime chain
"""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest import TestCase

from src.adapters.hermes_kernel_launcher import (
    HermesKernelLauncher,
    LaunchMode,
    LaunchPlan,
    SmokeResult,
)
from src.adapters.hermes_local_kernel_adapter import (
    HermesLocalKernelAdapter,
    LocalKernelSmokeReport,
)
from src.review.contracts import ReviewBrief


class TestHermesKernelLauncherDryRun(TestCase):
    """Test launcher dry-run mode with various path configurations."""

    def test_dry_run_with_valid_paths(self):
        """Dry-run with existing kernel path should be viable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kernel = Path(tmpdir) / "kernel"
            kernel.mkdir()
            overlay = Path(tmpdir) / "overlays"
            overlay.mkdir()
            for sub in ("skills", "memory", "config", "prompts"):
                (overlay / sub).mkdir()

            launcher = HermesKernelLauncher(kernel_path=kernel, overlays_path=overlay)
            plan = asyncio.run(launcher.dry_run())

            self.assertTrue(plan.viable)
            self.assertTrue(plan.kernel_exists)
            self.assertEqual(len(plan.errors), 0)
            self.assertEqual(plan.mode, "dry_run")
            for sub in ("skills", "memory", "config", "prompts"):
                self.assertTrue(plan.overlay_dirs_found.get(sub, False))

    def test_dry_run_with_missing_kernel(self):
        """Dry-run with non-existent kernel should NOT be viable."""
        launcher = HermesKernelLauncher(
            kernel_path=Path("/tmp/nonexistent_kernel_12345"),
        )
        plan = asyncio.run(launcher.dry_run())

        self.assertFalse(plan.viable)
        self.assertFalse(plan.kernel_exists)
        self.assertGreater(len(plan.errors), 0)

    def test_dry_run_without_overlay(self):
        """Dry-run without overlay should add a warning but may be viable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kernel = Path(tmpdir) / "kernel"
            kernel.mkdir()

            launcher = HermesKernelLauncher(kernel_path=kernel, overlays_path=None)
            plan = asyncio.run(launcher.dry_run())

            self.assertTrue(plan.viable)
            self.assertIsNone(plan.overlay_root)
            self.assertGreater(len(plan.warnings), 0)

    def test_inspect_returns_launch_plan(self):
        """inspect() should return a LaunchPlan dataclass."""
        launcher = HermesKernelLauncher(kernel_path=Path("/tmp/nonexistent"))
        plan = launcher.inspect()
        self.assertIsInstance(plan, LaunchPlan)


class TestHermesKernelLauncherSmoke(TestCase):
    """Test launcher smoke mode."""

    def test_smoke_with_viable_kernel(self):
        """Smoke with a valid kernel dir (but no run_agent.py) should succeed with warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kernel = Path(tmpdir) / "kernel"
            kernel.mkdir()

            launcher = HermesKernelLauncher(kernel_path=kernel)
            result = asyncio.run(launcher.smoke(payload={"test": True}))

            self.assertIsInstance(result, SmokeResult)
            self.assertTrue(result.success)
            self.assertEqual(result.mode, "smoke")
            self.assertEqual(result.payload_echo, {"test": True})
            # Should have warning about missing run_agent.py
            self.assertTrue(
                any("run_agent.py" in w for w in (result.plan.warnings if result.plan else []))
            )

    def test_smoke_with_missing_kernel(self):
        """Smoke with missing kernel should fail gracefully."""
        launcher = HermesKernelLauncher(
            kernel_path=Path("/tmp/nonexistent_kernel_12345"),
        )
        result = asyncio.run(launcher.smoke())

        self.assertFalse(result.success)
        self.assertIn("not viable", result.message.lower())


class TestHermesLocalKernelAdapter(TestCase):
    """Test the local kernel adapter smoke exercise and non-default behavior."""

    def test_adapter_not_available_by_default(self):
        """Adapter should NOT be available by default."""
        adapter = HermesLocalKernelAdapter()
        self.assertFalse(adapter.available)

    def test_health_check_reports_not_enabled(self):
        """Health check should report local_kernel_available_not_enabled."""
        adapter = HermesLocalKernelAdapter()
        health = asyncio.run(adapter.health_check())
        self.assertFalse(health["available"])
        self.assertEqual(health["mode"], "local_kernel_available_not_enabled")

    def test_review_returns_degraded_when_not_enabled(self):
        """review() should return a degraded packet when not enabled."""
        adapter = HermesLocalKernelAdapter()
        brief = ReviewBrief(
            review_id="test-001",
            review_object_type="construction_scheme",
        )
        packet = asyncio.run(adapter.review(brief))
        self.assertTrue(packet.degraded)
        self.assertEqual(packet.error, "not_enabled")

    def test_smoke_exercise_without_launcher(self):
        """smoke_exercise without a launcher should report error."""
        adapter = HermesLocalKernelAdapter(launcher=None)
        report = asyncio.run(adapter.smoke_exercise())

        self.assertIsInstance(report, LocalKernelSmokeReport)
        self.assertFalse(report.launcher_available)
        self.assertGreater(len(report.errors), 0)

    def test_smoke_exercise_with_launcher(self):
        """smoke_exercise with a valid launcher should produce a report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kernel = Path(tmpdir) / "kernel"
            kernel.mkdir()
            overlay = Path(tmpdir) / "overlays"
            overlay.mkdir()
            for sub in ("skills", "memory", "config", "prompts"):
                (overlay / sub).mkdir()

            launcher = HermesKernelLauncher(kernel_path=kernel, overlays_path=overlay)
            adapter = HermesLocalKernelAdapter(launcher=launcher)

            brief = ReviewBrief(
                review_id="smoke-001",
                review_object_type="construction_scheme",
            )
            report = asyncio.run(adapter.smoke_exercise(brief=brief))

            self.assertIsInstance(report, LocalKernelSmokeReport)
            self.assertTrue(report.launcher_available)
            self.assertIsNotNone(report.smoke_result)
            self.assertTrue(report.smoke_result.success)
            self.assertIsNotNone(report.review_packet)
            self.assertEqual(report.review_packet.review_id, "smoke-001")
            self.assertTrue(report.review_packet.degraded)
            self.assertEqual(report.review_packet.error, "smoke_only")


class TestMainChainIsolation(TestCase):
    """Verify that local kernel components do not leak into main chain."""

    def test_main_dependencies_does_not_import_local_kernel(self):
        """main_dependencies.py must not reference HermesLocalKernelAdapter."""
        main_deps = Path(__file__).resolve().parents[1] / "src" / "main_dependencies.py"
        if not main_deps.exists():
            self.skipTest("main_dependencies.py not found")

        text = main_deps.read_text(encoding="utf-8")
        self.assertNotIn("HermesLocalKernelAdapter", text)
        self.assertNotIn("hermes_local_kernel_adapter", text)
        self.assertNotIn("HermesKernelLauncher", text)
        self.assertNotIn("run_local_hermes_smoke", text)
