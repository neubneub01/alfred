"""
context_load — load markdown / text files from the /context mount.

The context directory is mounted from NFS at /mnt/nfs/ai-context (host)
mapped to /context inside the container.

Args schema:
    path (str, required) — relative path like "career/resume-base.md"
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from tools.registry import BaseTool

CONTEXT_ROOT = Path(os.getenv("CONTEXT_ROOT", "/context"))

# Maximum file size to load (256 KB) — prevents accidental memory blowup
MAX_FILE_SIZE = 256 * 1024


class Tool(BaseTool):
    name = "context_load"
    description = (
        "Load a markdown or text file from the context library. "
        "Use for career docs, templates, homelab docs, etc."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "Relative path within the context library, "
                    "e.g. 'career/resume-base.md' or 'homelab/00_index.md'."
                ),
            },
        },
        "required": ["path"],
    }

    async def execute(self, args: dict[str, Any]) -> str:
        rel_path = args["path"]

        # Resolve and validate — prevent path traversal
        target = (CONTEXT_ROOT / rel_path).resolve()
        if not str(target).startswith(str(CONTEXT_ROOT.resolve())):
            return f"Error: path traversal blocked: {rel_path}"

        if not target.is_file():
            # List available files in the parent directory as a hint
            parent = target.parent
            if parent.is_dir():
                available = sorted(
                    str(p.relative_to(CONTEXT_ROOT))
                    for p in parent.iterdir()
                    if p.is_file()
                )
                hint = "\n".join(available[:20]) if available else "(empty directory)"
                return f"Error: file not found: {rel_path}\n\nAvailable in {parent.name}/:\n{hint}"
            return f"Error: file not found: {rel_path}"

        if target.stat().st_size > MAX_FILE_SIZE:
            return f"Error: file too large ({target.stat().st_size} bytes, max {MAX_FILE_SIZE})"

        try:
            content = target.read_text(encoding="utf-8")
            return content
        except Exception as exc:
            return f"Error: could not read {rel_path}: {exc}"
