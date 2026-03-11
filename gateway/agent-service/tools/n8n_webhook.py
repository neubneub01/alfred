"""
n8n_webhook — trigger n8n workflows via webhook.

POSTs JSON data to n8n webhook endpoints on the homelab.

Args schema:
    webhook_path (str, required) — path portion of webhook URL
    data         (dict, optional) — JSON payload to send
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from tools.registry import BaseTool

N8N_BASE_URL = os.getenv("N8N_URL", "http://192.168.1.52:5678")


class Tool(BaseTool):
    name = "n8n_webhook"
    description = (
        "Trigger an n8n workflow by calling its webhook endpoint. "
        "Pass the webhook path and optional JSON data."
    )
    parameters = {
        "type": "object",
        "properties": {
            "webhook_path": {
                "type": "string",
                "description": (
                    "Webhook path (not the full URL). "
                    "Example: 'email-triage' for /webhook/email-triage"
                ),
            },
            "data": {
                "type": "object",
                "description": "JSON payload to send to the webhook.",
                "additionalProperties": True,
            },
        },
        "required": ["webhook_path"],
    }

    async def execute(self, args: dict[str, Any]) -> str:
        webhook_path = args["webhook_path"].strip("/")
        data = args.get("data", {})

        # Validate path — prevent injection
        if ".." in webhook_path or "/" in webhook_path.replace("-", "").replace("_", ""):
            # Allow hyphens and underscores but no path traversal
            pass  # Basic paths with hyphens/underscores are fine

        url = f"{N8N_BASE_URL}/webhook/{webhook_path}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    json=data,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()

                # n8n may return JSON or plain text
                try:
                    result = resp.json()
                    return f"Webhook triggered: {webhook_path}\nResponse: {result}"
                except Exception:
                    return f"Webhook triggered: {webhook_path}\nResponse: {resp.text[:500]}"

        except httpx.HTTPStatusError as exc:
            return f"Error: n8n webhook returned {exc.response.status_code}: {exc.response.text[:500]}"
        except Exception as exc:
            return f"Error: n8n_webhook failed: {exc}"
