"""
paperless — interact with Paperless-ngx API for document search and tagging.

Paperless-ngx runs on the homelab at http://192.168.1.221:8000.
Auth token is read from PAPERLESS_TOKEN env var.

Supported actions:
    search — search documents by query
    tag    — add tags to a document
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from tools.registry import BaseTool

PAPERLESS_URL = os.getenv("PAPERLESS_URL", "http://192.168.1.221:8000/api")
PAPERLESS_TOKEN = os.getenv("PAPERLESS_TOKEN", "")


class Tool(BaseTool):
    name = "paperless_search"
    description = (
        "Search documents in Paperless-ngx. "
        "Returns document titles, IDs, and snippets matching the query."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for document content or title.",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (default 10).",
                "default": 10,
            },
        },
        "required": ["query"],
    }

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if PAPERLESS_TOKEN:
            headers["Authorization"] = f"Token {PAPERLESS_TOKEN}"
        return headers

    async def execute(self, args: dict[str, Any]) -> str:
        query = args["query"]
        limit = args.get("limit", 10)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{PAPERLESS_URL}/documents/",
                    params={
                        "query": query,
                        "page_size": limit,
                        "ordering": "-created",
                    },
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()

            results = data.get("results", [])
            if not results:
                return f"No documents found for query: {query}"

            lines: list[str] = [f"Found {data.get('count', len(results))} documents:\n"]
            for doc in results:
                doc_id = doc.get("id", "?")
                title = doc.get("title", "(untitled)")
                created = doc.get("created", "")[:10]
                correspondent = doc.get("correspondent_name", "")
                tags = ", ".join(doc.get("tag_names", []))
                content_preview = (doc.get("content", "") or "")[:200]

                lines.append(f"  [{doc_id}] {title}")
                if correspondent:
                    lines.append(f"      Correspondent: {correspondent}")
                if created:
                    lines.append(f"      Created: {created}")
                if tags:
                    lines.append(f"      Tags: {tags}")
                if content_preview:
                    lines.append(f"      Preview: {content_preview}...")
                lines.append("")

            return "\n".join(lines)

        except httpx.HTTPStatusError as exc:
            return f"Error: Paperless returned {exc.response.status_code}: {exc.response.text[:500]}"
        except Exception as exc:
            return f"Error: paperless_search failed: {exc}"


class TagTool(BaseTool):
    """Separate tool for tagging documents — registered manually if needed."""

    name = "paperless_tag"
    description = "Add tags to a document in Paperless-ngx by document ID."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "integer",
                "description": "Paperless document ID.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of tag IDs to add to the document.",
            },
        },
        "required": ["document_id", "tags"],
    }

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if PAPERLESS_TOKEN:
            headers["Authorization"] = f"Token {PAPERLESS_TOKEN}"
        return headers

    async def execute(self, args: dict[str, Any]) -> str:
        doc_id = args["document_id"]
        tag_ids = args["tags"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # First, get current tags
                resp = await client.get(
                    f"{PAPERLESS_URL}/documents/{doc_id}/",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                doc = resp.json()

                current_tags = doc.get("tags", [])
                merged_tags = list(set(current_tags + tag_ids))

                # Update document with merged tags
                resp = await client.patch(
                    f"{PAPERLESS_URL}/documents/{doc_id}/",
                    json={"tags": merged_tags},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return f"Tagged document {doc_id} with tag IDs: {tag_ids}"

        except httpx.HTTPStatusError as exc:
            return f"Error: Paperless returned {exc.response.status_code}: {exc.response.text[:500]}"
        except Exception as exc:
            return f"Error: paperless_tag failed: {exc}"
