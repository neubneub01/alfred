"""
fastmail — interact with Fastmail via JMAP protocol.

Supports:
    search — search emails by query
    draft  — create a draft email

Auth token is read from FASTMAIL_TOKEN env var.
JMAP endpoint: https://api.fastmail.com/jmap/session
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from tools.registry import BaseTool

FASTMAIL_TOKEN = os.getenv("FASTMAIL_TOKEN", "")
JMAP_SESSION_URL = "https://api.fastmail.com/jmap/session"


class Tool(BaseTool):
    name = "fastmail_search"
    description = (
        "Search emails in Fastmail. "
        "Returns subject, from, date, and preview of matching emails."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (supports Fastmail search syntax).",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 10).",
                "default": 10,
            },
        },
        "required": ["query"],
    }

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {FASTMAIL_TOKEN}",
        }

    async def _get_session(self, client: httpx.AsyncClient) -> dict:
        """Fetch JMAP session to get API URL and account ID."""
        resp = await client.get(JMAP_SESSION_URL, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def execute(self, args: dict[str, Any]) -> str:
        if not FASTMAIL_TOKEN:
            return "Error: FASTMAIL_TOKEN not configured"

        query = args["query"]
        limit = args.get("limit", 10)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                session = await self._get_session(client)
                api_url = session["apiUrl"]
                account_id = session["primaryAccounts"]["urn:ietf:params:jmap:mail"]

                # JMAP Email/query + Email/get in one request
                jmap_request = {
                    "using": [
                        "urn:ietf:params:jmap:core",
                        "urn:ietf:params:jmap:mail",
                    ],
                    "methodCalls": [
                        [
                            "Email/query",
                            {
                                "accountId": account_id,
                                "filter": {"text": query},
                                "sort": [{"property": "receivedAt", "isAscending": False}],
                                "limit": limit,
                            },
                            "query",
                        ],
                        [
                            "Email/get",
                            {
                                "accountId": account_id,
                                "#ids": {
                                    "resultOf": "query",
                                    "name": "Email/query",
                                    "path": "/ids",
                                },
                                "properties": [
                                    "subject",
                                    "from",
                                    "receivedAt",
                                    "preview",
                                ],
                            },
                            "get",
                        ],
                    ],
                }

                resp = await client.post(
                    api_url,
                    json=jmap_request,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                # Parse results
                method_responses = data.get("methodResponses", [])
                emails: list[dict] = []
                for response in method_responses:
                    if response[0] == "Email/get":
                        emails = response[1].get("list", [])

                if not emails:
                    return f"No emails found for query: {query}"

                lines: list[str] = [f"Found {len(emails)} emails:\n"]
                for email in emails:
                    subject = email.get("subject", "(no subject)")
                    from_list = email.get("from", [])
                    sender = from_list[0].get("email", "unknown") if from_list else "unknown"
                    received = email.get("receivedAt", "")[:16]
                    preview = email.get("preview", "")[:150]

                    lines.append(f"  Subject: {subject}")
                    lines.append(f"  From: {sender}")
                    lines.append(f"  Date: {received}")
                    lines.append(f"  Preview: {preview}")
                    lines.append("")

                return "\n".join(lines)

        except httpx.HTTPStatusError as exc:
            return f"Error: Fastmail returned {exc.response.status_code}: {exc.response.text[:500]}"
        except Exception as exc:
            return f"Error: fastmail_search failed: {exc}"


class DraftTool(BaseTool):
    """Create a draft email in Fastmail."""

    name = "fastmail_draft"
    description = "Create a draft email in Fastmail."
    parameters = {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address.",
            },
            "subject": {
                "type": "string",
                "description": "Email subject line.",
            },
            "body": {
                "type": "string",
                "description": "Email body text (plain text).",
            },
        },
        "required": ["to", "subject", "body"],
    }

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {FASTMAIL_TOKEN}",
        }

    async def _get_session(self, client: httpx.AsyncClient) -> dict:
        resp = await client.get(JMAP_SESSION_URL, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def execute(self, args: dict[str, Any]) -> str:
        if not FASTMAIL_TOKEN:
            return "Error: FASTMAIL_TOKEN not configured"

        to_addr = args["to"]
        subject = args["subject"]
        body = args["body"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                session = await self._get_session(client)
                api_url = session["apiUrl"]
                account_id = session["primaryAccounts"]["urn:ietf:params:jmap:mail"]

                # Find Drafts mailbox
                jmap_request = {
                    "using": [
                        "urn:ietf:params:jmap:core",
                        "urn:ietf:params:jmap:mail",
                        "urn:ietf:params:jmap:submission",
                    ],
                    "methodCalls": [
                        [
                            "Mailbox/query",
                            {
                                "accountId": account_id,
                                "filter": {"role": "drafts"},
                            },
                            "findDrafts",
                        ],
                        [
                            "Email/set",
                            {
                                "accountId": account_id,
                                "create": {
                                    "draft1": {
                                        "#mailboxIds": {
                                            "resultOf": "findDrafts",
                                            "name": "Mailbox/query",
                                            "path": "/ids",
                                        },
                                        "to": [{"email": to_addr}],
                                        "subject": subject,
                                        "bodyValues": {
                                            "1": {
                                                "value": body,
                                                "isEncodingProblem": False,
                                            }
                                        },
                                        "textBody": [
                                            {
                                                "partId": "1",
                                                "type": "text/plain",
                                            }
                                        ],
                                        "keywords": {"$draft": True},
                                    }
                                },
                            },
                            "createDraft",
                        ],
                    ],
                }

                resp = await client.post(
                    api_url,
                    json=jmap_request,
                    headers=self._headers(),
                )
                resp.raise_for_status()

                return f"Draft created: to={to_addr}, subject='{subject}'"

        except httpx.HTTPStatusError as exc:
            return f"Error: Fastmail returned {exc.response.status_code}: {exc.response.text[:500]}"
        except Exception as exc:
            return f"Error: fastmail_draft failed: {exc}"
