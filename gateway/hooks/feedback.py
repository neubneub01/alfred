"""
Feedback Hook — Classification feedback loop.
Links user satisfaction (thumbs up/down) to router classification.

Integration: Open WebUI webhook on rating → POST to sidecar → this module.
Or: standalone FastAPI sidecar on port 4001 (see below).

Deploy to: /opt/litellm/hooks/feedback.py
"""

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("litellm.feedback")

CONFIG_DIR = Path(os.environ.get("LITELLM_CONFIG_DIR", "/app/config"))
DB_PATH = CONFIG_DIR / "data" / "litellm.db"

FEEDBACK_DDL = """
CREATE TABLE IF NOT EXISTS feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    request_id  TEXT NOT NULL,
    rating      INTEGER NOT NULL,
    alias       TEXT,
    model       TEXT,
    comment     TEXT
);
CREATE INDEX IF NOT EXISTS idx_feedback_request_id ON feedback(request_id);
CREATE INDEX IF NOT EXISTS idx_feedback_alias ON feedback(alias);
"""

_initialized = False


def _ensure_table():
    global _initialized
    if _initialized:
        return
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.executescript(FEEDBACK_DDL)
        _initialized = True
        logger.info("Feedback table initialized at %s", DB_PATH)
    except Exception as e:
        logger.error("Failed to init feedback table: %s", e)


def record_feedback(
    request_id: str,
    rating: int,
    alias: Optional[str] = None,
    model: Optional[str] = None,
    comment: Optional[str] = None,
) -> bool:
    """Record user feedback. rating: 1 = thumbs up, -1 = thumbs down."""
    _ensure_table()
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                """INSERT INTO feedback (timestamp, request_id, rating, alias, model, comment)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    request_id,
                    rating,
                    alias,
                    model,
                    comment,
                ),
            )
        return True
    except Exception as e:
        logger.error("Feedback write failed: %s", e)
        return False


def get_feedback_stats(alias: Optional[str] = None, hours: int = 24) -> dict:
    """Get feedback stats for an alias over the last N hours."""
    _ensure_table()
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            if alias:
                rows = conn.execute(
                    """SELECT rating, COUNT(*) as cnt FROM feedback
                       WHERE alias = ? AND timestamp > datetime('now', ?)
                       GROUP BY rating""",
                    (alias, f"-{hours} hours"),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT rating, COUNT(*) as cnt FROM feedback
                       WHERE timestamp > datetime('now', ?)
                       GROUP BY rating""",
                    (f"-{hours} hours",),
                ).fetchall()

            stats = {"positive": 0, "negative": 0}
            for row in rows:
                if row["rating"] > 0:
                    stats["positive"] = row["cnt"]
                elif row["rating"] < 0:
                    stats["negative"] = row["cnt"]
            stats["total"] = stats["positive"] + stats["negative"]
            stats["satisfaction"] = (
                stats["positive"] / stats["total"] if stats["total"] > 0 else None
            )
            return stats
    except Exception as e:
        logger.error("Feedback stats failed: %s", e)
        return {"positive": 0, "negative": 0, "total": 0, "satisfaction": None}
