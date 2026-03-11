"""
Pre-Call Hook — AI Productivity Engine Gateway
Deploy to: /opt/litellm/hooks/pre_call.py

5-stage routing pipeline with PipelineHealth tracking:
  1. Deterministic image detection
  2. Alias resolution (hint bypass)
  3. Classification (qwen3.5:4b on Host B)
  4. System prompt injection (from YAML)
  5. Cache control (Anthropic ephemeral)

Register in config.yaml:
  litellm_settings:
    callbacks: ["hooks.pre_call.pre_call_router"]
"""

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

import httpx
import yaml
from litellm.integrations.custom_logger import CustomLogger

logger = logging.getLogger("litellm.pre_call")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Docker mounts /opt/litellm → /app/config
CONFIG_DIR = Path(os.environ.get("LITELLM_CONFIG_DIR", "/app/config"))
SYSTEM_PROMPTS_PATH = CONFIG_DIR / "system-prompts.yaml"
CLASSIFICATION_PROMPT_PATH = CONFIG_DIR / "classification-prompt.txt"

# Router model — qwen3.5:4b on Host B LXC 501
ROUTER_URL = "http://192.168.1.41:11434/api/chat"
ROUTER_MODEL = "qwen3.5:4b"
ROUTER_TIMEOUT = 3.0  # seconds

# ntfy — Host B LXC 201
NTFY_URL = "http://192.168.1.38:8090/ai-gateway"
NTFY_TIMEOUT = 5.0

CONFIDENCE_THRESHOLD = 0.55
DEFAULT_MODEL = "claude-sonnet-4-6"   # infrastructure failure → safe
LOW_CONFIDENCE_ALIAS = "chat"          # ambiguity → cheap

NTFY_COOLDOWN = 300  # 5 minutes per stage
CONSECUTIVE_FAILURE_THRESHOLD = 5

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Alias Map
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VALID_ALIASES = {
    "code", "analyze", "agent", "long-context", "chat",
    "summarize", "batch-triage", "vision", "private",
}

# Canonical + shorthand hints → canonical alias
ALIAS_MAP = {
    # Canonical (identity)
    "code": "code",
    "analyze": "analyze",
    "agent": "agent",
    "long-context": "long-context",
    "chat": "chat",
    "summarize": "summarize",
    "batch-triage": "batch-triage",
    "vision": "vision",
    "private": "private",
    # Shorthand hints
    "analyse": "analyze",
    "triage": "batch-triage",
    "batch": "batch-triage",
    "summary": "summarize",
    "sum": "summarize",
    "img": "vision",
    "image": "vision",
    "sensitive": "private",
    "long": "long-context",
    "lc": "long-context",
}

# Aliases whose primary model is Anthropic (for cache control)
ANTHROPIC_ALIASES = {"code", "analyze", "agent"}

# Aliases that use Ollama (primary or fallback) — guard against low max_tokens
# qwen3.5 thinking mode consumes all tokens, leaving content empty
OLLAMA_ALIASES = {
    "batch-triage", "summarize", "private",  # Primary Ollama
    "code", "analyze", "agent", "chat", "vision",  # Ollama in fallback chain
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Default Classification Prompt
# Used when /app/config/classification-prompt.txt is absent
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFAULT_CLASSIFICATION_PROMPT = """\
You are a request classifier for an AI gateway. Analyze the user's message \
and return ONLY a JSON object with exactly three fields:

{"alias": "<alias>", "privacy": <bool>, "confidence": <float>}

Alias values (pick exactly one):
- code: programming, debugging, code review, software engineering
- analyze: tax/finance reasoning, complex analysis, deep research
- agent: multi-step tool-use workflows, autonomous task execution
- long-context: processing documents or codebases over 30k tokens
- chat: simple conversation, rewriting, casual questions
- summarize: condensing content, meeting notes, document summaries
- batch-triage: classification tasks, sorting, filtering, scoring items
- vision: image or screenshot analysis (only when image data is described)
- private: any sensitive/confidential personal, financial, tax, or medical data

Set "privacy" to true if the message contains sensitive personal, financial, \
tax, or medical information that should never leave the local network.

Set "confidence" to a float between 0.0 and 1.0 reflecting how certain you \
are about the alias choice.

Output ONLY the JSON object. No explanation, no markdown fences, no extra text."""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Metadata helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _set_meta(data, key, value):
    """Store routing metadata in data['metadata'] — NOT top-level.

    LiteLLM passes unknown top-level keys as API params to upstream providers.
    Anthropic/OpenAI reject them. The 'metadata' dict is LiteLLM-internal.
    """
    meta = data.setdefault("metadata", {})
    meta[key] = value


def _get_meta(data, key, default=None):
    """Read routing metadata from data['metadata']."""
    return data.get("metadata", {}).get(key, default)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Severity Model + Pipeline Health
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class Severity(IntEnum):
    LOW = 1       # Cosmetic — no routing impact
    MEDIUM = 2    # Degraded — using fallback model
    HIGH = 3      # Routing failed entirely


@dataclass
class StageResult:
    stage: str
    failed: bool = False
    severity: Severity = Severity.LOW
    error: str = ""
    impact: str = ""


@dataclass
class PipelineHealth:
    results: list = field(default_factory=list)
    request_id: str = ""

    def record_failure(self, stage, severity, error, impact):
        self.results.append(StageResult(
            stage=stage, failed=True, severity=severity,
            error=str(error), impact=impact,
        ))

    def record_success(self, stage):
        self.results.append(StageResult(stage=stage))

    @property
    def failed_stages(self):
        return [r for r in self.results if r.failed]

    @property
    def max_severity(self):
        severities = [r.severity for r in self.results if r.failed]
        return max(severities) if severities else Severity.LOW

    @property
    def has_failures(self):
        return any(r.failed for r in self.results)

    def to_metadata(self):
        """Serialize for attachment to request data (consumed by post-call hook)."""
        return {
            "request_id": self.request_id,
            "ok": not self.has_failures,
            "max_severity": self.max_severity.name if self.has_failures else None,
            "stages": [
                {
                    "stage": r.stage,
                    "ok": not r.failed,
                    **({"severity": r.severity.name, "error": r.error,
                         "impact": r.impact} if r.failed else {}),
                }
                for r in self.results
            ],
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pre-Call Hook
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PreCallRouter(CustomLogger):
    """LiteLLM pre-call hook implementing 5-stage routing pipeline."""

    def __init__(self):
        super().__init__()
        self._system_prompts = {}
        self._classification_prompt = ""
        self._loaded = False
        self._consecutive_failures = {}
        self._last_ntfy = {}

    # ── Config Loading ───────────────────────────────

    def _load_config(self):
        """Load system prompts and classification prompt from disk (once)."""
        if self._loaded:
            return

        # System prompts
        try:
            if SYSTEM_PROMPTS_PATH.exists():
                with open(SYSTEM_PROMPTS_PATH) as f:
                    self._system_prompts = yaml.safe_load(f) or {}
                logger.info("Loaded system prompts for: %s", list(self._system_prompts.keys()))
            else:
                logger.warning("System prompts not found: %s", SYSTEM_PROMPTS_PATH)
        except Exception as e:
            logger.error("Failed to load system prompts: %s", e)

        # Classification prompt — fall back to built-in default
        try:
            if CLASSIFICATION_PROMPT_PATH.exists():
                loaded = CLASSIFICATION_PROMPT_PATH.read_text().strip()
                if loaded:
                    self._classification_prompt = loaded
                    logger.info("Loaded classification prompt (%d chars)", len(loaded))
                else:
                    self._classification_prompt = DEFAULT_CLASSIFICATION_PROMPT
                    logger.info("Classification prompt file empty, using built-in default")
            else:
                self._classification_prompt = DEFAULT_CLASSIFICATION_PROMPT
                logger.info("Classification prompt file not found, using built-in default")
        except Exception as e:
            self._classification_prompt = DEFAULT_CLASSIFICATION_PROMPT
            logger.error("Failed to load classification prompt, using default: %s", e)

        self._loaded = True

    # ── Stage 1: Deterministic Image Detection ───────

    def _detect_images(self, data, health):
        """Scan messages for image_url or base64 image data. Pure string matching, zero cost."""
        try:
            for msg in data.get("messages", []):
                content = msg.get("content")

                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        # OpenAI-format: {"type": "image_url", "image_url": {"url": "..."}}
                        if block.get("type") == "image_url":
                            return self._route_vision(data, health), True
                        # Anthropic-format: {"type": "image", ...}
                        if block.get("type") == "image":
                            return self._route_vision(data, health), True
                        # Check nested image_url.url for base64 data URI
                        image_url = block.get("image_url")
                        if isinstance(image_url, dict):
                            url = image_url.get("url", "")
                        elif isinstance(image_url, str):
                            url = image_url
                        else:
                            continue
                        if url and "data:image/" in url:
                            return self._route_vision(data, health), True

                elif isinstance(content, str) and "data:image/" in content:
                    return self._route_vision(data, health), True

            health.record_success("image_detection")
            return data, False

        except Exception as e:
            health.record_failure(
                stage="image_detection",
                severity=Severity.LOW,
                error=str(e),
                impact="Image detection skipped; classification will handle routing",
            )
            return data, False

    @staticmethod
    def _route_vision(data, health):
        data["model"] = "vision"
        _set_meta(data, "_alias", "vision")
        _set_meta(data, "_routed_by", "image_detection")
        health.record_success("image_detection")
        return data

    # ── Stage 2: Alias Resolution ────────────────────

    def _resolve_alias(self, data, health):
        """If model is a known alias or hint, resolve it. Returns (data, resolved)."""
        model = data.get("model", "")

        # "auto" needs classification
        if model == "auto":
            health.record_success("alias_resolution")
            return data, False

        # Known alias/hint → canonical
        canonical = ALIAS_MAP.get(model)
        if canonical:
            data["model"] = canonical
            _set_meta(data, "_alias", canonical)
            _set_meta(data, "_routed_by", "alias_hint")
            health.record_success("alias_resolution")
            return data, True

        # Explicit model name (e.g. "claude-sonnet-4-6") → passthrough
        _set_meta(data, "_routed_by", "passthrough")
        health.record_success("alias_resolution")
        return data, True

    # ── Stage 3: Classification ──────────────────────

    async def _call_router_model(self, data):
        """Call qwen3.5:4b at 192.168.1.41 for prompt classification.

        Returns: {"alias": str, "privacy": bool, "confidence": float}
        """
        # Extract last user message for classification
        user_text = ""
        for msg in reversed(data.get("messages", [])):
            if msg.get("role") != "user":
                continue
            content = msg.get("content", "")
            if isinstance(content, str):
                user_text = content
            elif isinstance(content, list):
                user_text = " ".join(
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            break

        if not user_text:
            raise ValueError("No user message found for classification")

        # Truncate to 2000 chars — enough signal, keeps latency low
        user_text = user_text[:2000]

        payload = {
            "model": ROUTER_MODEL,
            "messages": [
                {"role": "system", "content": self._classification_prompt},
                {"role": "user", "content": user_text},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0, "num_predict": 128},
        "keep_alive": "24h",
        }

        async with httpx.AsyncClient(timeout=ROUTER_TIMEOUT) as client:
            resp = await client.post(ROUTER_URL, json=payload)
            resp.raise_for_status()
            result = resp.json()
            content = result.get("message", {}).get("content", "")
            return json.loads(content)

    async def _classify_request(self, data, health):
        """Classify request via router model. Apply confidence threshold.

        Confidence < 0.55 → chat (ambiguity is cheap).
        Timeout / error → claude-sonnet-4-6 (failure is safe).
        Privacy flag → private (stays local).
        """
        try:
            result = await self._call_router_model(data)
            alias = result.get("alias", "chat")
            confidence = float(result.get("confidence", 0.0))
            privacy = result.get("privacy", False)

            # Validate alias
            if alias not in VALID_ALIASES:
                logger.warning("Router returned unknown alias '%s', defaulting to chat", alias)
                alias = "chat"

            # Privacy override — always keep local
            if privacy:
                alias = "private"
            elif confidence < CONFIDENCE_THRESHOLD:
                logger.info(
                    "Low confidence %.2f for alias '%s', falling back to '%s'",
                    confidence, alias, LOW_CONFIDENCE_ALIAS,
                )
                alias = LOW_CONFIDENCE_ALIAS

            data["model"] = alias
            _set_meta(data, "_alias", alias)
            _set_meta(data, "_confidence", confidence)
            _set_meta(data, "_privacy", privacy)
            _set_meta(data, "_routed_by", "classifier")
            health.record_success("classification")
            return data

        except (asyncio.TimeoutError, httpx.TimeoutException):
            data["model"] = DEFAULT_MODEL
            _set_meta(data, "_routed_by", "fallback_timeout")
            health.record_failure(
                stage="classification",
                severity=Severity.MEDIUM,
                error="Router model timed out (>3s)",
                impact="Falling back to %s" % DEFAULT_MODEL,
            )
            return data

        except json.JSONDecodeError as e:
            data["model"] = DEFAULT_MODEL
            _set_meta(data, "_routed_by", "fallback_parse_error")
            health.record_failure(
                stage="classification",
                severity=Severity.MEDIUM,
                error="Router returned malformed JSON: %s" % e,
                impact="Falling back to %s" % DEFAULT_MODEL,
            )
            return data

        except Exception as e:
            data["model"] = DEFAULT_MODEL
            _set_meta(data, "_routed_by", "fallback_error")
            health.record_failure(
                stage="classification",
                severity=Severity.MEDIUM,
                error=str(e),
                impact="Falling back to %s" % DEFAULT_MODEL,
            )
            return data

    # ── Stage 4: System Prompt Injection ─────────────

    def _inject_system_prompt(self, data, health):
        """Inject alias-specific system prompt from YAML. Skip if caller provides one."""
        try:
            alias = _get_meta(data, "_alias")
            if not alias or alias not in self._system_prompts:
                health.record_success("system_prompt")
                return data

            messages = data.get("messages", [])

            # Skip if caller already provided a system message (n8n sends its own)
            if any(msg.get("role") == "system" for msg in messages):
                health.record_success("system_prompt")
                return data

            # Prepend system prompt
            system_text = self._system_prompts[alias]
            data["messages"] = [
                {"role": "system", "content": system_text},
                *messages,
            ]
            health.record_success("system_prompt")
            return data

        except Exception as e:
            health.record_failure(
                stage="system_prompt",
                severity=Severity.LOW,
                error=str(e),
                impact="Request proceeds without system prompt",
            )
            return data

    # ── Stage 5: Cache Control ───────────────────────

    def _apply_cache_control(self, data, health):
        """Add cache_control ephemeral to system prompt for Anthropic models.

        Saves 90% on system prompt tokens. Non-Anthropic providers ignore it
        via drop_params: true in config.yaml.
        """
        try:
            alias = _get_meta(data, "_alias", "")
            model = data.get("model", "")

            is_anthropic = (
                alias in ANTHROPIC_ALIASES
                or model.startswith("claude-")
                or model.startswith("anthropic/")
            )
            if not is_anthropic:
                health.record_success("cache_control")
                return data

            messages = data.get("messages", [])
            if not messages or messages[0].get("role") != "system":
                health.record_success("cache_control")
                return data

            system_msg = messages[0]
            content = system_msg.get("content", "")

            # Convert string content to block format with cache_control
            if isinstance(content, str) and content:
                system_msg["content"] = [{
                    "type": "text",
                    "text": content,
                    "cache_control": {"type": "ephemeral"},
                }]
            elif isinstance(content, list):
                # Add cache_control to the last text block
                for block in reversed(content):
                    if isinstance(block, dict) and block.get("type") == "text":
                        block["cache_control"] = {"type": "ephemeral"}
                        break

            health.record_success("cache_control")
            return data

        except Exception as e:
            health.record_failure(
                stage="cache_control",
                severity=Severity.LOW,
                error=str(e),
                impact="Anthropic prompt caching disabled for this request",
            )
            return data

    # ── Health Reporting & ntfy Escalation ────────────

    def _update_failure_counters(self, health):
        """Track consecutive failures per stage. Reset counter on success."""
        for result in health.results:
            if result.failed:
                self._consecutive_failures[result.stage] = (
                    self._consecutive_failures.get(result.stage, 0) + 1
                )
            else:
                self._consecutive_failures[result.stage] = 0

    async def _escalate_health(self, health):
        """Evaluate escalation rules and send ntfy notifications."""
        now = time.monotonic()
        notifications = []

        for result in health.failed_stages:
            if result.severity == Severity.HIGH:
                if self._check_cooldown(result.stage, now):
                    notifications.append((
                        "HIGH: %s" % result.stage,
                        "%s\nImpact: %s\nRequest: %s" % (result.error, result.impact, health.request_id),
                        "urgent",
                    ))

        for stage, count in self._consecutive_failures.items():
            if count >= CONSECUTIVE_FAILURE_THRESHOLD:
                if self._check_cooldown("persistent_%s" % stage, now):
                    notifications.append((
                        "Persistent failure: %s" % stage,
                        "%d consecutive failures\nRequest: %s" % (count, health.request_id),
                        "high",
                    ))

        if len(health.failed_stages) >= 3:
            if self._check_cooldown("systemic", now):
                failed_names = ", ".join(r.stage for r in health.failed_stages)
                notifications.append((
                    "Systemic degradation",
                    "Failed stages: %s\nRequest: %s" % (failed_names, health.request_id),
                    "urgent",
                ))

        for title, body, priority in notifications:
            await self._send_ntfy(title, body, priority)

    def _check_cooldown(self, key, now):
        """Return True if cooldown has elapsed for this notification key."""
        last = self._last_ntfy.get(key, 0.0)
        if now - last >= NTFY_COOLDOWN:
            self._last_ntfy[key] = now
            return True
        return False

    async def _send_ntfy(self, title, body, priority="default"):
        """Fire-and-forget notification via ntfy."""
        try:
            async with httpx.AsyncClient(timeout=NTFY_TIMEOUT) as client:
                await client.post(
                    NTFY_URL,
                    content=body.encode(),
                    headers={
                        "Title": title,
                        "Priority": priority,
                        "Tags": "robot,warning",
                    },
                )
        except Exception as e:
            logger.error("Failed to send ntfy notification: %s", e)

    # ── Main Hook Entry Point ────────────────────────

    async def async_pre_call_hook(
        self,
        user_api_key_dict,
        cache,
        data,
        call_type,
    ):
        """Five-stage pre-call pipeline with health tracking."""
        self._load_config()

        request_id = data.get("litellm_call_id", str(uuid.uuid4()))
        health = PipelineHealth(request_id=request_id)

        # Stage 1: Deterministic image check
        data, routed = self._detect_images(data, health)
        if not routed:
            # Stage 2: Alias resolution
            data, routed = self._resolve_alias(data, health)
            if not routed:
                # Stage 3: Classification (model="auto")
                data = await self._classify_request(data, health)

        # Stage 4: System prompt injection (always runs)
        data = self._inject_system_prompt(data, health)

        # Stage 4b: Ollama thinking-mode guard
        # qwen3.5 uses thinking mode which consumes max_tokens before producing content.
        # If client specifies a low max_tokens, strip it so config.yaml default (8192) applies.
        alias = _get_meta(data, "_alias", "")
        if alias in OLLAMA_ALIASES:
            current_max = data.get("max_tokens")
            if current_max is not None and current_max < 4096:
                data.pop("max_tokens", None)
                logger.info("Stripped client max_tokens=%d for Ollama alias '%s' — using config default", current_max, alias)

        # Stage 5: Cache control (always runs)
        data = self._apply_cache_control(data, health)

        # Final safety net: model must never leave as "auto"
        if data.get("model") == "auto":
            data["model"] = DEFAULT_MODEL
            _set_meta(data, "_routed_by", "safety_net")
            health.record_failure(
                stage="safety_net",
                severity=Severity.HIGH,
                error="Model still 'auto' after all pipeline stages",
                impact="Emergency fallback to %s" % DEFAULT_MODEL,
            )

        # Health reporting
        self._update_failure_counters(health)
        if health.has_failures:
            asyncio.create_task(self._escalate_health(health))

        # Attach pipeline metadata for post-call hook logging
        _set_meta(data, "_pipeline_health", health.to_metadata())

        logger.info(
            "[%s] model=%s alias=%s confidence=%s routed_by=%s failures=%d",
            request_id[:8],
            data.get("model"),
            _get_meta(data, "_alias", "none"),
            _get_meta(data, "_confidence", "N/A"),
            _get_meta(data, "_routed_by", "unknown"),
            len(health.failed_stages),
        )

        return data


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Module-level instance — referenced by LiteLLM config
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pre_call_router = PreCallRouter()
