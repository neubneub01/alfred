"""
LiteLLM Post-Call Hook — AI Gateway
Deploy to: /opt/litellm/hooks/post_call.py

Three responsibilities:
  1. Alias-specific validation dispatch (non-streaming only)
  2. Escalation on validation failure (once only, next model in chain)
  3. Request + escalation logging to SQLite

Escalation policy (from AI-PLAN section 2):
  - Escalate once only — never retry the same model
  - Never silently drop data — every give-up returns an error or best attempt
  - Escalation latency budget: 10 seconds max

Register in config.yaml:
  litellm_settings:
    success_callback: ["hooks.post_call.post_call_handler"]
"""

import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

import litellm
from litellm.integrations.custom_logger import CustomLogger

logger = logging.getLogger("litellm.post_call")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIG_DIR = Path(os.environ.get("LITELLM_CONFIG_DIR", "/app/config"))
DB_PATH = CONFIG_DIR / "data" / "litellm.db"

ESCALATION_TIMEOUT = 10.0  # seconds — per plan

# Escalation chains per alias — actual model identifiers for litellm.acompletion().
# These must be real provider/model strings, NOT proxy alias names (fb/...).
# Primary model fails validation → try chain[0] → chain[1] → fail.
ESCALATION_CHAINS = {
    "batch-triage": [
        {"model": "ollama/qwen3.5:27b", "api_base": "http://192.168.1.220:11434"},
        {"model": "gpt-5-mini"},
    ],
    "summarize": [
        {"model": "ollama/qwen3.5:27b", "api_base": "http://192.168.1.220:11434"},
    ],
}

# Primary model name per alias (used to determine chain position)
PRIMARY_MODELS: dict[str, str] = {
    "batch-triage": "batch-triage",
    "summarize": "summarize",
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Validator Registry (lazy import)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_validators = None


def _get_validators():
    """Lazy-load validators from the central registry."""
    global _validators
    if _validators is None:
        try:
            from validators import VALIDATORS

            _validators = VALIDATORS
            logger.info("Loaded validators: %s", list(_validators.keys()))
        except ImportError:
            logger.warning("Could not import validators — validation disabled")
            _validators = {}
    return _validators


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SQLite Schema
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS requests (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp         TEXT    NOT NULL,
    request_id        TEXT    NOT NULL,
    client            TEXT,
    original_model    TEXT,
    resolved_model    TEXT,
    alias             TEXT,
    confidence        REAL,
    input_tokens      INTEGER DEFAULT 0,
    output_tokens     INTEGER DEFAULT 0,
    latency_ms        REAL    DEFAULT 0,
    cost              REAL    DEFAULT 0,
    validation_status TEXT    DEFAULT 'n/a'
);

CREATE TABLE IF NOT EXISTS escalations (
    id                           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp                    TEXT    NOT NULL,
    request_id                   TEXT    NOT NULL,
    original_model               TEXT    NOT NULL,
    escalation_target            TEXT    NOT NULL,
    validator_trigger            TEXT,
    original_input_tokens        INTEGER DEFAULT 0,
    original_output_tokens       INTEGER DEFAULT 0,
    escalation_input_tokens      INTEGER DEFAULT 0,
    escalation_output_tokens     INTEGER DEFAULT 0,
    total_latency_ms             REAL    DEFAULT 0,
    escalation_success           INTEGER DEFAULT 0,
    escalation_validation_status TEXT
);

CREATE INDEX IF NOT EXISTS idx_requests_timestamp  ON requests(timestamp);
CREATE INDEX IF NOT EXISTS idx_requests_alias      ON requests(alias);
CREATE INDEX IF NOT EXISTS idx_requests_request_id ON requests(request_id);
CREATE INDEX IF NOT EXISTS idx_escalations_timestamp  ON escalations(timestamp);
CREATE INDEX IF NOT EXISTS idx_escalations_request_id ON escalations(request_id);
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Post-Call Handler
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PostCallHandler(CustomLogger):
    """LiteLLM post-call hook: validate, escalate, log.

    Hook methods:
      async_post_call_success_hook — validate + escalate (runs before response reaches client)
      async_log_success_event      — log request + escalation to SQLite
      async_log_failure_event      — log failed LLM calls
    """

    def __init__(self):
        super().__init__()
        self._db_initialized = False
        # Per-request state shared between post_call_success_hook and log_success_event.
        # Key: request_id, Value: validation/escalation metadata.
        self._request_state: dict[str, dict] = {}

    # ── DB ────────────────────────────────────────────

    def _ensure_db(self):
        """Create DB file and tables on first use."""
        if self._db_initialized:
            return
        try:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(DB_PATH)) as conn:
                conn.executescript(SCHEMA_DDL)
            self._db_initialized = True
            logger.info("SQLite initialized: %s", DB_PATH)
        except Exception as e:
            logger.error("Failed to initialize SQLite: %s", e)

    def _db_insert(self, sql: str, params: tuple = ()) -> None:
        """Execute a single INSERT with auto-commit."""
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                conn.execute(sql, params)
        except Exception as e:
            logger.error("SQLite write failed: %s — %s", sql[:80], e)

    # ── Metadata Helpers ─────────────────────────────

    @staticmethod
    def _get_alias(kwargs: dict) -> Optional[str]:
        """Extract alias from request data. Checks multiple locations."""
        litellm_params = kwargs.get("litellm_params") or {}
        metadata = litellm_params.get("metadata") or {}
        proxy_req = litellm_params.get("proxy_server_request") or {}
        body = proxy_req.get("body") or {}

        for source in (kwargs, metadata, body):
            if not isinstance(source, dict):
                continue
            alias = source.get("_alias")
            if alias:
                return alias

        # Infer from model group name
        model = kwargs.get("model_group") or kwargs.get("model", "")
        if model in ESCALATION_CHAINS:
            return model
        return None

    @staticmethod
    def _get_request_id(kwargs: dict) -> str:
        litellm_params = kwargs.get("litellm_params") or {}
        return (
            kwargs.get("litellm_call_id")
            or litellm_params.get("litellm_call_id", "")
            or "unknown"
        )

    @staticmethod
    def _is_streaming(kwargs: dict) -> bool:
        return bool(kwargs.get("stream"))

    @staticmethod
    def _is_escalated(kwargs: dict) -> bool:
        litellm_params = kwargs.get("litellm_params") or {}
        metadata = litellm_params.get("metadata") or {}
        return bool(metadata.get("_escalated"))

    @staticmethod
    def _get_output_text(response_obj: Any) -> str:
        try:
            return response_obj.choices[0].message.content or ""
        except (AttributeError, IndexError):
            return ""

    @staticmethod
    def _get_usage(response_obj: Any) -> tuple[int, int]:
        """Returns (input_tokens, output_tokens)."""
        try:
            usage = response_obj.usage
            return (
                getattr(usage, "prompt_tokens", 0) or 0,
                getattr(usage, "completion_tokens", 0) or 0,
            )
        except AttributeError:
            return 0, 0

    # ── Validation ───────────────────────────────────

    @staticmethod
    def _validate(alias: str, output: str) -> tuple[bool, str]:
        """Run alias-specific validator. Returns (valid, error_message)."""
        validators = _get_validators()
        validator = validators.get(alias)
        if not validator:
            return True, ""
        try:
            return validator(output)
        except Exception as e:
            logger.error("Validator crash for alias '%s': %s", alias, e)
            return False, f"Validator exception: {e}"

    # ── Escalation ───────────────────────────────────

    @staticmethod
    def _get_escalation_target(alias, current_model):
        """Find the next model dict in the escalation chain.

        Returns dict with 'model' key (and optionally 'api_base'), or None at end of chain.
        """
        chain = ESCALATION_CHAINS.get(alias)
        if not chain:
            return None

        # Primary model → escalate to chain[0]
        primary = PRIMARY_MODELS.get(alias)
        if current_model == primary or current_model == alias:
            return chain[0]

        # Already in the chain → step to next
        for i, entry in enumerate(chain):
            if entry.get("model") == current_model:
                if i + 1 < len(chain):
                    return chain[i + 1]
                return None  # end of chain

        # Unknown position — try first fallback
        return chain[0] if chain else None

    async def _escalate(
        self,
        alias,
        target,
        messages,
        request_id,
    ):
        """Re-dispatch to escalation model. Returns (response, latency_ms) or (None, latency_ms).

        target is a dict: {"model": "ollama/qwen3.5:27b", "api_base": "http://..."}
        """
        target_model = target["model"]
        start = time.monotonic()
        try:
            kwargs = dict(
                model=target_model,
                messages=messages,
                stream=False,
                timeout=ESCALATION_TIMEOUT,
                metadata={
                    "_escalated": True,
                    "_original_request_id": request_id,
                },
            )
            if "api_base" in target:
                kwargs["api_base"] = target["api_base"]

            response = await litellm.acompletion(**kwargs)
            latency = (time.monotonic() - start) * 1000
            logger.info(
                "[%s] Escalation to %s completed in %.0fms",
                request_id[:8],
                target_model,
                latency,
            )
            return response, latency
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            logger.error(
                "[%s] Escalation to %s failed after %.0fms: %s",
                request_id[:8],
                target_model,
                latency,
                e,
            )
            return None, latency

    # ── SQLite Logging ───────────────────────────────

    def _log_request(
        self,
        request_id: str,
        client: str,
        original_model: str,
        resolved_model: str,
        alias: Optional[str],
        confidence: Optional[float],
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        cost: float,
        validation_status: str,
    ):
        self._ensure_db()
        self._db_insert(
            """INSERT INTO requests
               (timestamp, request_id, client, original_model, resolved_model,
                alias, confidence, input_tokens, output_tokens, latency_ms,
                cost, validation_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                request_id,
                client,
                original_model,
                resolved_model,
                alias,
                confidence,
                input_tokens,
                output_tokens,
                latency_ms,
                cost,
                validation_status,
            ),
        )

    def _log_escalation(
        self,
        request_id: str,
        original_model: str,
        escalation_target: str,
        validator_trigger: str,
        orig_input_tokens: int,
        orig_output_tokens: int,
        esc_input_tokens: int,
        esc_output_tokens: int,
        total_latency_ms: float,
        escalation_success: bool,
        escalation_validation_status: str,
    ):
        self._ensure_db()
        self._db_insert(
            """INSERT INTO escalations
               (timestamp, request_id, original_model, escalation_target,
                validator_trigger, original_input_tokens, original_output_tokens,
                escalation_input_tokens, escalation_output_tokens,
                total_latency_ms, escalation_success, escalation_validation_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                request_id,
                original_model,
                escalation_target,
                validator_trigger,
                orig_input_tokens,
                orig_output_tokens,
                esc_input_tokens,
                esc_output_tokens,
                total_latency_ms,
                1 if escalation_success else 0,
                escalation_validation_status,
            ),
        )

    # ── Hook: Validate + Escalate ────────────────────

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: dict,
        response: Any,
    ):
        """Validate non-streaming responses. Escalate on failure.

        Runs BEFORE the response reaches the client. On successful escalation,
        the response object is modified in place so the client receives the
        escalated (valid) output instead of the original (invalid) output.
        """
        # Skip: streaming, already-escalated, or no validator for this alias
        if data.get("stream"):
            return

        metadata = data.get("metadata", {})
        if metadata.get("_escalated"):
            return

        alias = self._get_alias(data)
        if not alias or alias not in _get_validators():
            return

        request_id = data.get("litellm_call_id", "unknown")
        output = self._get_output_text(response)
        valid, error = self._validate(alias, output)

        if valid:
            self._request_state[request_id] = {"validation_status": "pass"}
            return

        logger.warning(
            "[%s] Validation failed for '%s': %s",
            request_id[:8],
            alias,
            error,
        )

        # Find escalation target
        current_model = data.get("model", alias)
        target = self._get_escalation_target(alias, current_model)

        if not target:
            self._request_state[request_id] = {
                "validation_status": "fail",
                "validation_error": error,
            }
            logger.error(
                "[%s] No escalation target for '%s' — giving up",
                request_id[:8],
                alias,
            )
            return

        # Escalate: re-dispatch to next model (once only)
        messages = data.get("messages", [])
        if not messages:
            self._request_state[request_id] = {
                "validation_status": "fail",
                "validation_error": error,
            }
            return

        orig_input, orig_output = self._get_usage(response)
        esc_response, esc_latency = await self._escalate(
            alias, target, messages, request_id
        )

        target_name = target["model"]

        if esc_response is None:
            self._request_state[request_id] = {
                "validation_status": "fail",
                "validation_error": error,
                "escalation_target": target_name,
                "escalation_success": False,
                "escalation_validation_status": "error",
                "escalation_latency_ms": esc_latency,
                "orig_input_tokens": orig_input,
                "orig_output_tokens": orig_output,
                "esc_input_tokens": 0,
                "esc_output_tokens": 0,
            }
            return

        # Validate escalation response
        esc_output_text = self._get_output_text(esc_response)
        esc_valid, esc_error = self._validate(alias, esc_output_text)
        esc_input, esc_output_tokens = self._get_usage(esc_response)
        esc_validation_status = "pass" if esc_valid else "fail"

        if esc_valid:
            try:
                response.choices = esc_response.choices
                if hasattr(esc_response, "usage"):
                    response.usage = esc_response.usage
                response.model = getattr(esc_response, "model", response.model)
                logger.info(
                    "[%s] Escalation to %s passed validation — response replaced",
                    request_id[:8],
                    target_name,
                )
            except Exception as e:
                logger.error("[%s] Failed to replace response: %s", request_id[:8], e)
        else:
            logger.warning(
                "[%s] Escalation to %s also failed validation: %s",
                request_id[:8],
                target_name,
                esc_error,
            )

        self._request_state[request_id] = {
            "validation_status": "fail",
            "validation_error": error,
            "escalation_target": target_name,
            "escalation_success": esc_valid,
            "escalation_validation_status": esc_validation_status,
            "escalation_latency_ms": esc_latency,
            "orig_input_tokens": orig_input,
            "orig_output_tokens": orig_output,
            "esc_input_tokens": esc_input,
            "esc_output_tokens": esc_output_tokens,
        }

    # ── Hook: Log Success ────────────────────────────

    async def async_log_success_event(
        self,
        kwargs: dict,
        response_obj: Any,
        start_time: Any,
        end_time: Any,
    ):
        """Log every successful request to SQLite. Record escalations if any."""
        try:
            request_id = self._get_request_id(kwargs)
            alias = self._get_alias(kwargs)
            is_streaming = self._is_streaming(kwargs)
            is_escalated = self._is_escalated(kwargs)

            # Extract metadata (safe access — any intermediate value may be None)
            litellm_params = kwargs.get("litellm_params") or {}
            metadata = litellm_params.get("metadata") or {}
            proxy_req = litellm_params.get("proxy_server_request") or {}
            body = proxy_req.get("body") or {}

            original_model = body.get("model", kwargs.get("model", ""))
            resolved_model = kwargs.get("model", "")
            confidence = (
                metadata.get("_confidence")
                or body.get("_confidence")
            )
            client = metadata.get("user_api_key_alias", "unknown")

            input_tokens, output_tokens = self._get_usage(response_obj)

            # Latency
            try:
                if hasattr(start_time, "timestamp") and hasattr(end_time, "timestamp"):
                    latency_ms = (end_time.timestamp() - start_time.timestamp()) * 1000
                else:
                    latency_ms = 0.0
            except Exception:
                latency_ms = 0.0

            # Cost
            try:
                cost = litellm.completion_cost(
                    model=resolved_model,
                    prompt_tokens=input_tokens,
                    completion_tokens=output_tokens,
                )
            except Exception:
                cost = 0.0

            # Validation status — read from state set by post_call_success_hook
            state = self._request_state.pop(request_id, {})

            if is_escalated:
                validation_status = "escalation"
            elif is_streaming:
                validation_status = "skip_streaming"
            else:
                validation_status = state.get("validation_status", "n/a")

            # Log request
            self._log_request(
                request_id=request_id,
                client=client,
                original_model=original_model,
                resolved_model=resolved_model,
                alias=alias,
                confidence=confidence,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost=cost,
                validation_status=validation_status,
            )

            # Log escalation if one occurred
            if state.get("escalation_target"):
                self._log_escalation(
                    request_id=request_id,
                    original_model=resolved_model,
                    escalation_target=state["escalation_target"],
                    validator_trigger=state.get("validation_error", ""),
                    orig_input_tokens=state.get("orig_input_tokens", input_tokens),
                    orig_output_tokens=state.get("orig_output_tokens", output_tokens),
                    esc_input_tokens=state.get("esc_input_tokens", 0),
                    esc_output_tokens=state.get("esc_output_tokens", 0),
                    total_latency_ms=latency_ms
                    + state.get("escalation_latency_ms", 0),
                    escalation_success=state.get("escalation_success", False),
                    escalation_validation_status=state.get(
                        "escalation_validation_status", ""
                    ),
                )

            logger.info(
                "[%s] logged: alias=%s model=%s tokens=%d/%d "
                "latency=%.0fms cost=$%.4f validation=%s",
                request_id[:8],
                alias,
                resolved_model,
                input_tokens,
                output_tokens,
                latency_ms,
                cost,
                validation_status,
            )

            # Safety: prevent unbounded state growth
            if len(self._request_state) > 1000:
                self._request_state.clear()
                logger.warning("Cleared stale request state (>1000 entries)")

        except Exception as e:
            logger.error("Post-call logging failed: %s", e, exc_info=True)

    # ── Hook: Log Failure ────────────────────────────

    async def async_log_failure_event(
        self,
        kwargs: dict,
        response_obj: Any,
        start_time: Any,
        end_time: Any,
    ):
        """Log failed LLM calls (timeouts, API errors, etc.)."""
        try:
            request_id = self._get_request_id(kwargs)
            alias = self._get_alias(kwargs)
            litellm_params = kwargs.get("litellm_params") or {}
            metadata = litellm_params.get("metadata") or {}
            proxy_req = litellm_params.get("proxy_server_request") or {}
            body = proxy_req.get("body") or {}

            original_model = body.get("model", kwargs.get("model", ""))
            resolved_model = kwargs.get("model", "")
            client = metadata.get("user_api_key_alias", "unknown")

            try:
                if hasattr(start_time, "timestamp") and hasattr(end_time, "timestamp"):
                    latency_ms = (end_time.timestamp() - start_time.timestamp()) * 1000
                else:
                    latency_ms = 0.0
            except Exception:
                latency_ms = 0.0

            self._log_request(
                request_id=request_id,
                client=client,
                original_model=original_model,
                resolved_model=resolved_model,
                alias=alias,
                confidence=None,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                cost=0.0,
                validation_status="error",
            )

            logger.warning(
                "[%s] failure logged: alias=%s model=%s latency=%.0fms",
                request_id[:8],
                alias,
                resolved_model,
                latency_ms,
            )

        except Exception as e:
            logger.error("Post-call failure logging failed: %s", e, exc_info=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Module-level instance — referenced by LiteLLM config
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

post_call_handler = PostCallHandler()
