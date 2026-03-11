"""
Tier 2 Agent Service — POST /v1/agent/run
Host C LXC 102, port 8100

FastAPI application that runs AI agents with tool access.
Each agent has a defined persona, tool allowlist, and cost limits.
All LLM calls route through the LiteLLM gateway.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent_loop import AgentRun, run_agent, _load_agent_config
from tools.registry import load_tools, BaseTool

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("agent-service")

# ── Globals ──────────────────────────────────────────────────────────────────

tool_registry: dict[str, BaseTool] = {}
start_time: float = 0.0

# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load tools on startup."""
    global tool_registry, start_time
    start_time = time.time()
    logger.info("Loading tool registry...")
    tool_registry = load_tools()
    logger.info("Agent service ready — %d tools loaded", len(tool_registry))
    yield
    logger.info("Agent service shutting down")


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Agent Service",
    description="Tier 2 Agent Framework — observe, think, act",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Request / Response models ────────────────────────────────────────────────

class AgentRequest(BaseModel):
    """Request body for POST /v1/agent/run."""
    agent: str = Field(
        ...,
        description="Agent ID: research, tax_prep, interview_prep, homelab_troubleshooter",
    )
    task: str = Field(
        ...,
        description="Natural language description of the task to perform",
        min_length=1,
        max_length=10000,
    )
    max_iterations: int = Field(
        default=10,
        ge=1,
        le=25,
        description="Maximum number of think-act iterations",
    )


class AgentResponse(BaseModel):
    """Response body from POST /v1/agent/run."""
    status: str = Field(..., description="Final status: complete, cost_ceiling, max_iterations, error")
    result: str = Field(..., description="Agent's final output or error message")
    iterations: int = Field(..., description="Number of iterations executed")
    cost: float = Field(..., description="Estimated cost in USD for this run")


class HealthResponse(BaseModel):
    """Response body from GET /health."""
    status: str
    uptime_seconds: float
    tools_loaded: int
    agents_available: list[str]


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint — reports service status and loaded tools."""
    from pathlib import Path
    import yaml

    # Load available agent names
    agents_available: list[str] = []
    config_path = Path(__file__).parent / "config" / "agents.yaml"
    try:
        with open(config_path) as f:
            agents = yaml.safe_load(f) or {}
        agents_available = list(agents.keys())
    except Exception:
        pass

    return HealthResponse(
        status="healthy",
        uptime_seconds=round(time.time() - start_time, 1),
        tools_loaded=len(tool_registry),
        agents_available=agents_available,
    )


@app.post("/v1/agent/run", response_model=AgentResponse)
async def run(req: AgentRequest) -> AgentResponse:
    """Run an agent with the given task.

    The agent loops through observe-think-act cycles, using its configured
    tools to accomplish the task. Returns the final result, iteration count,
    and cost.
    """
    # Validate agent exists
    config = _load_agent_config(req.agent)
    if config is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown agent: '{req.agent}'. Check GET /health for available agents.",
        )

    logger.info("Agent run request: agent=%s, task=%s", req.agent, req.task[:100])

    # Build and execute agent run
    agent_run = AgentRun(
        agent_id=req.agent,
        task=req.task,
        max_iterations=req.max_iterations,
    )

    try:
        result = await run_agent(agent_run, tool_registry)
    except Exception as exc:
        logger.exception("Unhandled error in agent %s", req.agent)
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {exc}",
        ) from exc

    return AgentResponse(
        status=result.status,
        result=result.result or "",
        iterations=result.iteration,
        cost=round(result.total_cost, 6),
    )


@app.get("/v1/agent/tools")
async def list_tools() -> dict:
    """List all registered tools and their schemas."""
    return {
        name: {
            "description": tool.description,
            "parameters": tool.parameters,
        }
        for name, tool in tool_registry.items()
    }
