"""
ntfy — send push notifications via ntfy server.

POSTs to the local ntfy instance on the homelab.

Args schema:
    title    (str, required) — notification title
    message  (str, required) — notification body
    priority (int, optional) — 1-5, default 3
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from tools.registry import BaseTool

NTFY_URL = os.getenv("NTFY_URL", "http://192.168.1.38:8090/ai-agents")


class Tool(BaseTool):
    name = "ntfy"
    description = (
        "Send a push notification to the user. "
        "Use when a long-running task completes or needs attention."
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Notification title.",
            },
            "message": {
                "type": "string",
                "description": "Notification body text.",
            },
            "priority": {
                "type": "integer",
                "description": "Priority 1 (min) to 5 (urgent). Default 3.",
                "default": 3,
                "minimum": 1,
                "maximum": 5,
            },
        },
        "required": ["title", "message"],
    }

    async def execute(self, args: dict[str, Any]) -> str:
        title = args["title"]
        message = args["message"]
        priority = str(args.get("priority", 3))

        headers = {
            "Title": title,
            "Priority": priority,
            "Tags": "robot",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    NTFY_URL,
                    content=message,
                    headers=headers,
                )
                resp.raise_for_status()
                return f"Notification sent: {title}"
        except httpx.HTTPStatusError as exc:
            return f"Error: ntfy returned {exc.response.status_code}: {exc.response.text[:300]}"
        except Exception as exc:
            return f"Error: ntfy failed: {exc}"
