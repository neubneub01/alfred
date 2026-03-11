"""
Tool registry — loads all tool modules and returns a dict of BaseTool instances.
Each tool inherits from BaseTool and implements execute(args).
"""

from __future__ import annotations

import importlib
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

# ── Base class all tools inherit from ────────────────────────────────────────

class BaseTool(ABC):
    """Abstract base for every agent tool."""

    name: str
    description: str
    parameters: dict  # JSON Schema for the tool arguments

    @abstractmethod
    async def execute(self, args: dict[str, Any]) -> str:
        """Run the tool with the given arguments and return a string result."""
        ...

    def openai_schema(self) -> dict:
        """Return the tool definition in OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# ── Registry of all built-in tool modules ────────────────────────────────────

_TOOL_MODULES: list[str] = [
    "tools.gateway_chat",
    "tools.context_load",
    "tools.ntfy",
    "tools.things",
    "tools.shell_exec",
    "tools.paperless",
    "tools.fastmail",
    "tools.web_search",
    "tools.n8n_webhook",
]


def load_tools() -> dict[str, BaseTool]:
    """Import every tool module and return {name: instance} dict."""
    registry: dict[str, BaseTool] = {}

    for module_path in _TOOL_MODULES:
        try:
            mod = importlib.import_module(module_path)
            tool_class = getattr(mod, "Tool", None)
            if tool_class is None:
                logger.warning("Module %s has no Tool class — skipped", module_path)
                continue
            instance: BaseTool = tool_class()
            registry[instance.name] = instance
            logger.info("Registered tool: %s", instance.name)
        except Exception:
            logger.exception("Failed to load tool module %s", module_path)

    logger.info("Loaded %d tools: %s", len(registry), list(registry.keys()))
    return registry
