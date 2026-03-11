"""
things — create Things 3 tasks/projects via the URL scheme.

Generates things:///json URLs for task creation. When running on the homelab
(Docker container), this returns the URL string for the caller to open on macOS.
When running locally, it could open the URL directly.

Args schema:
    title    (str, required) — task title
    notes    (str, optional) — task notes / description
    area     (str, optional) — Things 3 area name
    tags     (list, optional) — list of tag strings
    deadline (str, optional) — ISO date string (YYYY-MM-DD)
"""

from __future__ import annotations

import json
import urllib.parse
from typing import Any

from tools.registry import BaseTool


class Tool(BaseTool):
    name = "things_create"
    description = (
        "Create a task in Things 3 via URL scheme. "
        "Returns the things:///json URL to execute."
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Task title.",
            },
            "notes": {
                "type": "string",
                "description": "Task notes or description.",
            },
            "area": {
                "type": "string",
                "description": "Things 3 area (Career, Finance & Admin, Fitness, Homelab, Personal, Tax & Advisory).",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of tags to apply.",
            },
            "deadline": {
                "type": "string",
                "description": "Deadline in YYYY-MM-DD format.",
            },
        },
        "required": ["title"],
    }

    async def execute(self, args: dict[str, Any]) -> str:
        item: dict[str, Any] = {
            "type": "to-do",
            "attributes": {
                "title": args["title"],
            },
        }

        attrs = item["attributes"]

        if "notes" in args and args["notes"]:
            attrs["notes"] = args["notes"]

        if "area" in args and args["area"]:
            attrs["area"] = args["area"]

        if "tags" in args and args["tags"]:
            attrs["tags"] = args["tags"]

        if "deadline" in args and args["deadline"]:
            attrs["deadline"] = args["deadline"]

        payload = json.dumps([item], separators=(",", ":"))
        encoded = urllib.parse.quote(payload, safe="")
        url = f"things:///json?data={encoded}"

        return f"Things URL created:\n{url}"
