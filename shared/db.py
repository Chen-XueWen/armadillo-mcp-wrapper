import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "governor.db")
VALID_STATUSES = {
    "PENDING",
    "APPROVED",
    "DENIED",
    "BLOCKED",
    "COMPLETED",
    "TIMEOUT",
    "FAILED",
}

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn

def init_db() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                tool_name TEXT,
                args TEXT,
                status TEXT,
                policy_reason TEXT,
                risk_level TEXT,
                agent_id TEXT
            )
            """
        )

        # Simple migration: try to add column if it doesn't exist.
        try:
            cursor.execute("ALTER TABLE requests ADD COLUMN agent_id TEXT")
        except sqlite3.OperationalError:
            pass

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON requests(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_agent ON requests(agent_id)")

def log_request(
    tool_name: str,
    args: Dict[str, Any],
    status: str,
    policy_reason: Optional[str],
    risk_level: str,
    agent_id: str = "Unknown",
) -> str:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid request status '{status}'")

    request_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    args_json = json.dumps(args)

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO requests (id, timestamp, tool_name, args, status, policy_reason, risk_level, agent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (request_id, timestamp, tool_name, args_json, status, policy_reason, risk_level, agent_id),
        )

    return request_id

def get_pending_requests() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM requests WHERE status = 'PENDING' ORDER BY timestamp DESC").fetchall()

    return [dict(row) for row in rows]

def update_status(request_id: str, new_status: str) -> None:
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid request status '{new_status}'")
    with get_connection() as conn:
        conn.execute("UPDATE requests SET status = ? WHERE id = ?", (new_status, request_id))

def get_request_status(request_id: str) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute("SELECT status FROM requests WHERE id = ?", (request_id,)).fetchone()

    return row[0] if row else None

if __name__ == "__main__":
    init_db()
