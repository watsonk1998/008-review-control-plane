"""
Hermes Kernel Launcher.

Status:
- future / skeleton
- not enabled in active runtime

Responsible for managing the execution environment, lifecycle, and 
overlay injections (skills, memory, config) for the isolated external/hermes-agent submodule.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class HermesKernelLauncher:
    """Manages the invocation of the local Hermes agent kernel."""
    
    def __init__(self, kernel_path: Path, overlays_path: Path | None = None):
        self.kernel_path = kernel_path
        self.overlays_path = overlays_path

    async def start(self) -> None:
        """
        Prepare environment and spawn the kernel process.
        TODO: Implement subprocess start, passing overlay boundaries as ENV or CLI args.
        """
        logger.info("[hermes_launcher] start() called (skeleton implementation).")
        pass
        
    async def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Send a payload to the kernel and await the response.
        TODO: Implement communication (e.g. process pipes or a local domain socket/port).
        """
        logger.warning("[hermes_launcher] invoke() is a skeleton placeholder.")
        return {}
        
    async def stop(self) -> None:
        """
        Gracefully terminate the sidecar/subprocess.
        """
        logger.info("[hermes_launcher] stop() called (skeleton implementation).")
        pass
