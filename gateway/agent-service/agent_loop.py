"""
Core agent loop — observe, think, act.

All LLM calls route through the LiteLLM gateway. The loop:
1. Sends the conversation to the gateway with tool definitions
2. If the model returns tool_calls, executes them and appends results
3. If the model returns content without tool_calls, the task is complete
4. Enforces cost ceilings, iteration limits, and context window management
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import yaml

from tools.registry import BaseTool

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

GATEWAY_URL = os.getenv(
    "GATEWAY_URL", "http://192.168.1.52:4000"
) + "/v1/chat/completions"
GATEWAY_KEY = os.getenv("GATEWAY_KEY", "")

MAX_ITERATIONS_DEFAULT = 10
MAX_ITERATIONS_HARD = 25
COST_CEILING_PER_RUN = 2.00  # dollars
DAILY_COST_BREAKER = 15.00   # dollars — circuit breaker for daily spend
CONTEXT_SUMMARIZE_THRESHOLD = 0.80  # summarize when > 80% of window

# Rough context window size (tokens) — conservative estimate for Claude Sonnet
CONTEXT_WINDOW_SIZE = 180_000

# Config directory
CONFIG_DIR = Path(__file__).parent / "config"

# Daily cost tracking file
COST_TRACKING_FILE = Path(__file__).parent / "data" / "daily_cost.json"


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class AgentRun:
    """Tracks the state of a single agent execution."""

    agent_id: str
    task: str
    model: str = "agent"
    tools: list[str] = field(default_factory=list)
    max_iterations: int = MAX_ITERATIONS_DEFAULT
    messages: list[dict[str, Any]] = field(default_factory=list)
    iteration: int = 0
    total_cost: float = 0.0
    status: str = "running"
    result: Any = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None


# ── Main agent loop ──────────────────────────────────────────────────────────

async def run_agent(run: AgentRun, tool_registry: dict[str, BaseTool]) -> AgentRun:
    """Execute the agent loop until task complete, max iterations, or cost ceiling."""

    # Load agent configuration
    agent_config = _load_agent_config(run.agent_id)
    if agent_config is None:
        run.status = "error"
        run.result = f"Unknown agent: {run.agent_id}"
        return run

    # Apply agent config
    run.model = agent_config.get("model", "agent")
    run.tools = agent_config.get("tools", [])
    effective_max = min(
        run.max_iterations,
        agent_config.get("max_iterations", MAX_ITERATIONS_DEFAULT),
        MAX_ITERATIONS_HARD,
    )

    # Check daily cost breaker
    if _get_daily_cost() >= DAILY_COST_BREAKER:
        run.status = "daily_cost_breaker"
        run.result = (
            f"Daily cost breaker tripped (${DAILY_COST_BREAKER:.2f}). "
            "No more agent runs until tomorrow."
        )
        logger.warning("Daily cost breaker: $%.2f reached", DAILY_COST_BREAKER)
        return run

    # Build tool definitions for the LLM (only tools this agent is allowed to use)
    tool_definitions = _build_tool_definitions(run.tools, tool_registry)

    # Build initial messages
    run.messages = [
        {"role": "system", "content": agent_config["system_prompt"]},
        {"role": "user", "content": run.task},
    ]

    logger.info(
        "Starting agent %s: task=%s, model=%s, max_iter=%d, tools=%s",
        run.agent_id, run.task[:80], run.model, effective_max, run.tools,
    )

    while run.iteration < effective_max:
        run.iteration += 1
        logger.info("Agent %s iteration %d/%d", run.agent_id, run.iteration, effective_max)

        # ── Cost check ───────────────────────────────────────────────────
        if run.total_cost >= COST_CEILING_PER_RUN:
            run.status = "cost_ceiling"
            run.result = (
                f"Cost ceiling reached (${run.total_cost:.4f} >= "
                f"${COST_CEILING_PER_RUN:.2f}). Partial results in conversation."
            )
            logger.warning("Cost ceiling hit for agent %s: $%.4f", run.agent_id, run.total_cost)
            break

        # ── Context window management ────────────────────────────────────
        usage_pct = _context_usage(run.messages)
        if usage_pct > CONTEXT_SUMMARIZE_THRESHOLD:
            logger.info(
                "Context at %.0f%% — summarizing history", usage_pct * 100
            )
            run.messages = await _summarize_history(run.messages)

        # ── Call gateway ─────────────────────────────────────────────────
        try:
            response = await _gateway_call(
                model=run.model,
                messages=run.messages,
                tools=tool_definitions if tool_definitions else None,
            )
        except Exception as exc:
            run.status = "error"
            run.result = f"Gateway call failed: {exc}"
            logger.exception("Gateway call failed on iteration %d", run.iteration)
            break

        # Track cost (LiteLLM includes cost in response metadata when available)
        iteration_cost = _extract_cost(response)
        run.total_cost += iteration_cost
        _add_daily_cost(iteration_cost)

        # ── Parse assistant response ─────────────────────────────────────
        choices = response.get("choices", [])
        if not choices:
            run.status = "error"
            run.result = "Gateway returned empty choices"
            break

        assistant_msg = choices[0].get("message", {})
        run.messages.append(assistant_msg)

        # ── Check for tool calls ─────────────────────────────────────────
        tool_calls = assistant_msg.get("tool_calls", [])
        if not tool_calls:
            # Agent is done — no more tool calls needed
            run.status = "complete"
            run.result = assistant_msg.get("content", "")
            logger.info(
                "Agent %s complete after %d iterations, cost=$%.4f",
                run.agent_id, run.iteration, run.total_cost,
            )
            break

        # ── Execute tool calls ───────────────────────────────────────────
        for tc in tool_calls:
            func = tc.get("function", {})
            tool_name = func.get("name", "")
            raw_args = func.get("arguments", "{}")

            # Parse arguments
            try:
                tool_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                tool_args = {"raw": raw_args}

            # Execute with validation
            if tool_name not in run.tools:
                tool_result = f"Error: tool '{tool_name}' not in this agent's allowlist: {run.tools}"
                logger.warning("Tool %s not in allowlist for agent %s", tool_name, run.agent_id)
            elif tool_name not in tool_registry:
                tool_result = f"Error: tool '{tool_name}' not found in registry"
                logger.warning("Tool %s not in registry", tool_name)
            else:
                try:
                    logger.info("Executing tool %s with args: %s", tool_name, str(tool_args)[:200])
                    tool_result = await tool_registry[tool_name].execute(tool_args)
                    logger.info("Tool %s returned %d chars", tool_name, len(str(tool_result)))
                except Exception as exc:
                    tool_result = f"Error executing {tool_name}: {exc}"
                    logger.exception("Tool execution failed: %s", tool_name)

            # Append tool result to conversation
            run.messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": str(tool_result)[:10000],  # Truncate very large results
            })

    # ── Finalize ─────────────────────────────────────────────────────────────

    if run.status == "running":
        run.status = "max_iterations"
        run.result = (
            f"Reached max iterations ({effective_max}). "
            "Partial progress in conversation history."
        )

    run.finished_at = time.time()
    elapsed = run.finished_at - run.started_at
    logger.info(
        "Agent %s finished: status=%s, iterations=%d, cost=$%.4f, elapsed=%.1fs",
        run.agent_id, run.status, run.iteration, run.total_cost, elapsed,
    )

    return run


# ── Helper functions ─────────────────────────────────────────────────────────

def _load_agent_config(agent_id: str) -> dict[str, Any] | None:
    """Load agent configuration from config/agents.yaml."""
    config_path = CONFIG_DIR / "agents.yaml"
    try:
        with open(config_path) as f:
            agents = yaml.safe_load(f)
        return agents.get(agent_id)
    except FileNotFoundError:
        logger.error("Agent config not found: %s", config_path)
        return None
    except Exception:
        logger.exception("Failed to load agent config")
        return None


def _build_tool_definitions(
    allowed_tools: list[str], registry: dict[str, BaseTool]
) -> list[dict]:
    """Build OpenAI-format tool definitions for the allowed tools."""
    definitions: list[dict] = []
    for tool_name in allowed_tools:
        tool = registry.get(tool_name)
        if tool:
            definitions.append(tool.openai_schema())
    return definitions


async def _gateway_call(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
) -> dict:
    """POST to the LiteLLM gateway and return the response JSON."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if GATEWAY_KEY:
        headers["Authorization"] = f"Bearer {GATEWAY_KEY}"

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(GATEWAY_URL, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


def _context_usage(messages: list[dict]) -> float:
    """Estimate what fraction of the context window is used.

    Rough heuristic: ~4 characters per token.
    """
    total_chars = sum(len(str(m)) for m in messages)
    estimated_tokens = total_chars / 4
    return estimated_tokens / CONTEXT_WINDOW_SIZE


async def _summarize_history(messages: list[dict]) -> list[dict]:
    """Condense old messages to free context space.

    Keeps: system prompt (first message), last 4 messages.
    Summarizes everything in between via the gateway.
    """
    if len(messages) <= 6:
        return messages  # Not enough to summarize

    system_msg = messages[0]
    middle_msgs = messages[1:-4]
    recent_msgs = messages[-4:]

    # Build a summary of the middle conversation
    middle_text = "\n".join(
        f"[{m.get('role', '?')}]: {str(m.get('content', ''))[:500]}"
        for m in middle_msgs
    )

    try:
        summary_response = await _gateway_call(
            model="summarize",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Summarize this agent conversation history concisely. "
                        "Preserve all key findings, tool results, decisions, and "
                        "remaining tasks. Use bullet points."
                    ),
                },
                {"role": "user", "content": middle_text},
            ],
        )
        summary = summary_response["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("Failed to summarize history — keeping original")
        return messages

    # Rebuild: system + summary + recent
    return [
        system_msg,
        {
            "role": "user",
            "content": f"[Previous conversation summary]\n{summary}",
        },
        *recent_msgs,
    ]


def _extract_cost(response: dict) -> float:
    """Extract cost from gateway response if available.

    LiteLLM may include cost in _litellm_params or usage metadata.
    Falls back to rough estimation based on token counts.
    """
    # Try direct cost field
    usage = response.get("usage", {})
    if "cost" in response:
        return float(response["cost"])

    # Estimate from token usage (~$0.003 per 1K input, ~$0.015 per 1K output for Sonnet)
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    estimated = (prompt_tokens * 0.003 + completion_tokens * 0.015) / 1000
    return estimated


def _get_daily_cost() -> float:
    """Read today's accumulated cost from the tracking file."""
    try:
        if not COST_TRACKING_FILE.exists():
            return 0.0
        data = json.loads(COST_TRACKING_FILE.read_text())
        today = time.strftime("%Y-%m-%d")
        return data.get(today, 0.0)
    except Exception:
        return 0.0


def _add_daily_cost(amount: float) -> None:
    """Add to today's cost in the tracking file."""
    if amount <= 0:
        return
    try:
        COST_TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, float] = {}
        if COST_TRACKING_FILE.exists():
            data = json.loads(COST_TRACKING_FILE.read_text())

        today = time.strftime("%Y-%m-%d")
        data[today] = data.get(today, 0.0) + amount

        # Prune entries older than 30 days
        cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - 30 * 86400))
        data = {k: v for k, v in data.items() if k >= cutoff}

        COST_TRACKING_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        logger.exception("Failed to update daily cost tracker")
