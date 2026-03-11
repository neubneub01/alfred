"""
Prometheus SQLite Exporter — AI Productivity Engine
Deploy to: /opt/litellm/monitoring/prometheus_exporter.py

Reads from the gateway's SQLite database and exposes Prometheus metrics
on port 9101. Metrics are refreshed every 60 seconds.

Run:
    DB_PATH=/opt/litellm/data/litellm.db python prometheus_exporter.py

Requires: prometheus_client (see requirements.txt)
"""

import logging
import os
import sqlite3
import sys
import threading
import time
from pathlib import Path

from prometheus_client import Counter, Gauge, start_http_server

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DB_PATH = Path(os.environ.get("DB_PATH", "/opt/litellm/data/litellm.db"))
EXPORTER_PORT = int(os.environ.get("EXPORTER_PORT", "9101"))
COLLECT_INTERVAL = int(os.environ.get("COLLECT_INTERVAL", "60"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_exporter")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Metric Definitions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ai_daily_cost_dollars = Gauge(
    "ai_daily_cost_dollars",
    "Total API cost in dollars for today (UTC)",
)

ai_local_inference_ratio = Gauge(
    "ai_local_inference_ratio",
    "Ratio of local (Ollama) requests to total requests in the last 24 hours",
)

ai_escalation_rate = Gauge(
    "ai_escalation_rate",
    "Fraction of requests that triggered escalation per alias (last 24h)",
    ["alias"],
)

ai_classification_latency_p95_ms = Gauge(
    "ai_classification_latency_p95_ms",
    "95th percentile classification latency in milliseconds (last 24h)",
)

ai_requests_total = Counter(
    "ai_requests_total",
    "Total number of requests processed",
    ["alias", "model"],
)

ai_router_model_loaded = Gauge(
    "ai_router_model_loaded",
    "1 if the router model responded within the last 5 minutes, 0 otherwise",
)

ai_feedback_positive_total = Counter(
    "ai_feedback_positive_total",
    "Total positive feedback events",
    ["alias"],
)

ai_feedback_negative_total = Counter(
    "ai_feedback_negative_total",
    "Total negative feedback events",
    ["alias"],
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Internal State
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Counters can only be incremented — track the last-seen totals to compute
# deltas between collection cycles.
_last_request_counts: dict[tuple[str, str], float] = {}
_last_feedback_pos: dict[str, float] = {}
_last_feedback_neg: dict[str, float] = {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Database Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _connect() -> sqlite3.Connection:
    """Open a read-only connection to the gateway SQLite database."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _query(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Execute a read query and return all rows."""
    try:
        cursor = conn.execute(sql, params)
        return cursor.fetchall()
    except sqlite3.OperationalError as e:
        logger.warning("Query failed: %s — %s", sql[:120], e)
        return []


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Check whether a table exists in the database."""
    rows = _query(
        conn,
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return len(rows) > 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Collection Logic
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def collect():
    """Query SQLite and update all Prometheus metrics.

    Called every COLLECT_INTERVAL seconds. Each query is wrapped in its own
    try/except so a single failure does not block the remaining metrics.
    """
    global _last_request_counts, _last_feedback_pos, _last_feedback_neg

    try:
        conn = _connect()
    except FileNotFoundError:
        logger.warning("Database file not found at %s — skipping collection", DB_PATH)
        ai_router_model_loaded.set(0)
        return
    except Exception as e:
        logger.error("Failed to connect to database: %s", e)
        ai_router_model_loaded.set(0)
        return

    try:
        # ── Daily Cost ────────────────────────────────────
        try:
            rows = _query(conn, """
                SELECT COALESCE(SUM(cost), 0) AS total_cost
                FROM requests
                WHERE date(timestamp) = date('now')
            """)
            if rows:
                ai_daily_cost_dollars.set(rows[0]["total_cost"])
        except Exception as e:
            logger.error("Failed to collect daily cost: %s", e)

        # ── Local Inference Ratio ─────────────────────────
        try:
            rows = _query(conn, """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN resolved_model LIKE 'ollama/%' THEN 1 ELSE 0 END) AS local_count
                FROM requests
                WHERE timestamp >= datetime('now', '-24 hours')
            """)
            if rows and rows[0]["total"] > 0:
                ratio = rows[0]["local_count"] / rows[0]["total"]
                ai_local_inference_ratio.set(ratio)
            else:
                ai_local_inference_ratio.set(0.0)
        except Exception as e:
            logger.error("Failed to collect local inference ratio: %s", e)

        # ── Escalation Rate per Alias ─────────────────────
        # Escalations are tracked in the separate `escalations` table.
        # Join against requests to get the alias, or count escalations
        # directly and compare against total requests per alias.
        try:
            if _table_exists(conn, "escalations"):
                # Total requests per alias in last 24h
                alias_totals = _query(conn, """
                    SELECT alias, COUNT(*) AS total
                    FROM requests
                    WHERE timestamp >= datetime('now', '-24 hours')
                      AND alias IS NOT NULL
                    GROUP BY alias
                """)
                alias_total_map = {row["alias"]: row["total"] for row in alias_totals}

                # Escalation count per alias (via request_id join)
                esc_rows = _query(conn, """
                    SELECT r.alias, COUNT(DISTINCT e.request_id) AS esc_count
                    FROM escalations e
                    JOIN requests r ON e.request_id = r.request_id
                    WHERE e.timestamp >= datetime('now', '-24 hours')
                      AND r.alias IS NOT NULL
                    GROUP BY r.alias
                """)
                esc_map = {row["alias"]: row["esc_count"] for row in esc_rows}

                # Set gauge for each alias that has traffic
                seen_aliases = set()
                for alias, total in alias_total_map.items():
                    esc_count = esc_map.get(alias, 0)
                    rate = esc_count / total if total > 0 else 0.0
                    ai_escalation_rate.labels(alias=alias).set(rate)
                    seen_aliases.add(alias)

                # Also set 0 for aliases with escalations but no matching requests
                for alias in esc_map:
                    if alias not in seen_aliases:
                        ai_escalation_rate.labels(alias=alias).set(0.0)
        except Exception as e:
            logger.error("Failed to collect escalation rate: %s", e)

        # ── Classification Latency p95 ────────────────────
        # We approximate p95 using the percentile approach on latency_ms
        # for requests routed by the classifier in the last 24h.
        try:
            rows = _query(conn, """
                SELECT latency_ms
                FROM requests
                WHERE timestamp >= datetime('now', '-24 hours')
                  AND latency_ms > 0
                ORDER BY latency_ms ASC
            """)
            if rows:
                latencies = [row["latency_ms"] for row in rows]
                p95_index = int(len(latencies) * 0.95)
                p95_index = min(p95_index, len(latencies) - 1)
                ai_classification_latency_p95_ms.set(latencies[p95_index])
            else:
                ai_classification_latency_p95_ms.set(0.0)
        except Exception as e:
            logger.error("Failed to collect classification latency: %s", e)

        # ── Requests Total (Counter) ──────────────────────
        # Counters can only go up. Query cumulative totals and increment
        # by the delta since the last collection.
        try:
            rows = _query(conn, """
                SELECT
                    COALESCE(alias, 'unknown') AS alias,
                    COALESCE(resolved_model, 'unknown') AS model,
                    COUNT(*) AS cnt
                FROM requests
                GROUP BY alias, resolved_model
            """)
            current_counts: dict[tuple[str, str], float] = {}
            for row in rows:
                key = (row["alias"], row["model"])
                current_counts[key] = row["cnt"]
                prev = _last_request_counts.get(key, 0)
                delta = row["cnt"] - prev
                if delta > 0:
                    ai_requests_total.labels(alias=key[0], model=key[1]).inc(delta)
            _last_request_counts = current_counts
        except Exception as e:
            logger.error("Failed to collect request totals: %s", e)

        # ── Router Model Health ───────────────────────────
        # Consider the router model "loaded" if there has been a request
        # in the last 5 minutes (the router is called on every auto-routed
        # request, so silence means it is down or unused).
        try:
            rows = _query(conn, """
                SELECT COUNT(*) AS recent
                FROM requests
                WHERE timestamp >= datetime('now', '-5 minutes')
            """)
            if rows and rows[0]["recent"] > 0:
                ai_router_model_loaded.set(1)
            else:
                ai_router_model_loaded.set(0)
        except Exception as e:
            logger.error("Failed to collect router model health: %s", e)

        # ── Feedback Counters ─────────────────────────────
        # The feedback table may not exist yet (created by a future
        # feedback endpoint). Handle gracefully.
        try:
            if _table_exists(conn, "feedback"):
                # Positive feedback
                pos_rows = _query(conn, """
                    SELECT COALESCE(alias, 'unknown') AS alias, COUNT(*) AS cnt
                    FROM feedback
                    WHERE sentiment = 'positive'
                    GROUP BY alias
                """)
                current_pos: dict[str, float] = {}
                for row in pos_rows:
                    a = row["alias"]
                    current_pos[a] = row["cnt"]
                    prev = _last_feedback_pos.get(a, 0)
                    delta = row["cnt"] - prev
                    if delta > 0:
                        ai_feedback_positive_total.labels(alias=a).inc(delta)
                _last_feedback_pos = current_pos

                # Negative feedback
                neg_rows = _query(conn, """
                    SELECT COALESCE(alias, 'unknown') AS alias, COUNT(*) AS cnt
                    FROM feedback
                    WHERE sentiment = 'negative'
                    GROUP BY alias
                """)
                current_neg: dict[str, float] = {}
                for row in neg_rows:
                    a = row["alias"]
                    current_neg[a] = row["cnt"]
                    prev = _last_feedback_neg.get(a, 0)
                    delta = row["cnt"] - prev
                    if delta > 0:
                        ai_feedback_negative_total.labels(alias=a).inc(delta)
                _last_feedback_neg = current_neg
        except Exception as e:
            logger.error("Failed to collect feedback metrics: %s", e)

    finally:
        conn.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Collection Loop
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _collection_loop():
    """Background thread that calls collect() every COLLECT_INTERVAL seconds."""
    while True:
        try:
            collect()
            logger.info("Collection complete")
        except Exception as e:
            logger.error("Unexpected error in collection loop: %s", e, exc_info=True)
        time.sleep(COLLECT_INTERVAL)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Entry Point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    logger.info("Starting AI Productivity Engine Prometheus exporter")
    logger.info("  DB_PATH:          %s", DB_PATH)
    logger.info("  EXPORTER_PORT:    %d", EXPORTER_PORT)
    logger.info("  COLLECT_INTERVAL: %ds", COLLECT_INTERVAL)

    # Start HTTP server for Prometheus scraping
    start_http_server(EXPORTER_PORT)
    logger.info("Metrics server listening on :%d/metrics", EXPORTER_PORT)

    # Run initial collection, then loop in a daemon thread
    collect()
    thread = threading.Thread(target=_collection_loop, daemon=True)
    thread.start()

    # Block main thread (KeyboardInterrupt exits cleanly)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down")
        sys.exit(0)


if __name__ == "__main__":
    main()
