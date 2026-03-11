"""
web_search — search the web for information.

Uses the gateway with a search-oriented prompt as the implementation.
If a SearXNG instance is available, it can be used as a primary source.

Args schema:
    query (str, required) — search query
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from tools.registry import BaseTool

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://192.168.1.52:4000") + "/v1/chat/completions"
GATEWAY_KEY = os.getenv("GATEWAY_KEY", "")
SEARXNG_URL = os.getenv("SEARXNG_URL", "")  # Optional: e.g. http://192.168.1.52:8888


class Tool(BaseTool):
    name = "web_search"
    description = (
        "Search the web for current information on a topic. "
        "Returns summarized search results."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            },
        },
        "required": ["query"],
    }

    async def _searxng_search(self, query: str) -> str | None:
        """Try SearXNG first if configured."""
        if not SEARXNG_URL:
            return None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{SEARXNG_URL}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "engines": "google,duckduckgo,brave",
                        "categories": "general",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            results = data.get("results", [])[:8]
            if not results:
                return None

            lines: list[str] = [f"Search results for: {query}\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "(untitled)")
                url = r.get("url", "")
                content = r.get("content", "")[:300]
                lines.append(f"{i}. {title}")
                lines.append(f"   URL: {url}")
                if content:
                    lines.append(f"   {content}")
                lines.append("")

            return "\n".join(lines)
        except Exception:
            return None  # Fall through to gateway

    async def _gateway_search(self, query: str) -> str:
        """Fallback: use the gateway with a search-oriented prompt."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if GATEWAY_KEY:
            headers["Authorization"] = f"Bearer {GATEWAY_KEY}"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    GATEWAY_URL,
                    json={
                        "model": "chat",
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are a web search assistant. Provide comprehensive, "
                                    "factual information about the query. Include specific details, "
                                    "dates, numbers, and sources where possible. Note clearly if "
                                    "information may be outdated based on your training cutoff."
                                ),
                            },
                            {
                                "role": "user",
                                "content": f"Search query: {query}\n\nProvide detailed, current information.",
                            },
                        ],
                        "stream": False,
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return f"[Gateway search for: {query}]\n\n{content}"

        except Exception as exc:
            return f"Error: web_search failed: {exc}"

    async def execute(self, args: dict[str, Any]) -> str:
        query = args["query"]

        # Try SearXNG first
        result = await self._searxng_search(query)
        if result:
            return result

        # Fallback to gateway
        return await self._gateway_search(query)
