"""
shell_exec — execute whitelisted shell commands only.

Safety: commands are validated against a strict prefix whitelist.
Only read-only / diagnostic commands are allowed.

Args schema:
    command (str, required) — the shell command to execute
"""

from __future__ import annotations

import asyncio
from typing import Any

from tools.registry import BaseTool

# Only these command prefixes are allowed — all are read-only diagnostics
WHITELIST: list[str] = [
    "curl -s",
    "docker ps",
    "docker logs --tail",
    "df -h",
    "free -m",
    "nvidia-smi",
    "systemctl status",
    "ping -c",
    "cat /proc/",
    "uptime",
    "docker stats --no-stream",
    "ip addr",
]

# Maximum execution time for any command
EXEC_TIMEOUT = 30


class Tool(BaseTool):
    name = "shell_exec"
    description = (
        "Execute a whitelisted shell command for diagnostics. "
        "Only read-only commands (docker ps, df, free, systemctl status, etc.) are allowed."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": (
                    "Shell command to execute. Must start with a whitelisted prefix: "
                    "curl -s, docker ps, docker logs --tail, df -h, free -m, "
                    "nvidia-smi, systemctl status, ping -c, cat /proc/"
                ),
            },
        },
        "required": ["command"],
    }

    async def execute(self, args: dict[str, Any]) -> str:
        cmd = args["command"].strip()

        # Validate against whitelist
        if not any(cmd.startswith(prefix) for prefix in WHITELIST):
            allowed = ", ".join(f'"{p}"' for p in WHITELIST)
            return (
                f"Error: command not whitelisted: {cmd}\n"
                f"Allowed prefixes: {allowed}"
            )

        # Block shell injection characters
        dangerous = [";", "&&", "||", "|", "`", "$(", ">>", ">"]
        for char in dangerous:
            if char in cmd:
                return f"Error: forbidden character/sequence in command: {char}"

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=EXEC_TIMEOUT
            )

            output = stdout.decode("utf-8", errors="replace")
            err_output = stderr.decode("utf-8", errors="replace")

            # Truncate very long outputs
            if len(output) > 10000:
                output = output[:10000] + "\n... (truncated)"
            if err_output:
                output += f"\nSTDERR: {err_output[:2000]}"

            return output if output.strip() else "(no output)"

        except asyncio.TimeoutError:
            return f"Error: command timed out after {EXEC_TIMEOUT}s: {cmd}"
        except Exception as exc:
            return f"Error: shell_exec failed: {exc}"
