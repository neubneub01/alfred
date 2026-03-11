"""
gateway_chat — send a prompt to the LiteLLM gateway and return the response.

Args schema:
    model   (str, optional)  — gateway alias, defaults to "chat"
    prompt  (str, required)  — the user prompt
    system  (str, optional)  — system prompt override
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from tools.registry import BaseTool

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://192.168.1.52:4000") + "/v1/chat/completions"
GATEWAY_KEY = os.getenv("GATEWAY_KEY", "")


class Tool(BaseTool):
    name = "gateway_chat"
    description = (
        "Send a prompt to the AI gateway and get a response. "
        "Use model='analyze' for complex reasoning, 'chat' for simple tasks."
    )
    parameters = {
        "type": "object",
        "properties": {
            "model": {
                "type": "string",
                "description": "Gateway model alias (chat, analyze, code, summarize).",
                "default": "chat",
            },
            "prompt": {
                "type": "string",
                "description": "The user prompt to send.",
            },
            "system": {
                "type": "string",
                "description": "Optional system prompt override.",
            },
        },
        "required": ["prompt"],
    }

    async def execute(self, args: dict[str, Any]) -> str:
        model = args.get("model", "chat")
        prompt = args["prompt"]
        system = args.get("system")

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if GATEWAY_KEY:
            headers["Authorization"] = f"Bearer {GATEWAY_KEY}"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    GATEWAY_URL,
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            return f"Error: gateway returned {exc.response.status_code}: {exc.response.text[:500]}"
        except Exception as exc:
            return f"Error: gateway_chat failed: {exc}"
