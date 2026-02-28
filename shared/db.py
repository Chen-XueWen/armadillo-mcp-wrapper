import sqlite3
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "governor.db")

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
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
    """)
    
    # Simple migration: try to add column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE requests ADD COLUMN agent_id TEXT")
    except sqlite3.OperationalError:
        pass # Column likely already exists
        
    conn.commit()
    conn.close()

def log_request(tool_name: str, args: Dict[str, Any], status: str, policy_reason: str, risk_level: str, agent_id: str = "Unknown") -> str:
    request_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    args_json = json.dumps(args)
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO requests (id, timestamp, tool_name, args, status, policy_reason, risk_level, agent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (request_id, timestamp, tool_name, args_json, status, policy_reason, risk_level, agent_id)
    )
    conn.commit()
    conn.close()
    return request_id

def get_pending_requests() -> List[Dict[str, Any]]:
    conn = get_connection()
    # Use row_factory to get dict-like access
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM requests WHERE status = 'PENDING' ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    
    requests = []
    for row in rows:
        requests.append(dict(row))
    return requests

def update_status(request_id: str, new_status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE requests SET status = ? WHERE id = ?", (new_status, request_id))
    conn.commit()
    conn.close()

def get_request_status(request_id: str) -> Optional[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM requests WHERE id = ?", (request_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# Initialize DB on import (or handle explicitly)
if __name__ == "__main__":
    init_db()
