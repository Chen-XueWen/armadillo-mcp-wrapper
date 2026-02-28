import sys
import os
import asyncio
import time
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List

# Add project root to sys.path to allow imports from shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import ToolCall, PolicyDecision
from backend.policy_engine import PolicyEngine
from shared.db import log_request, update_status, get_request_status, init_db, get_connection
import pandas as pd

app = FastAPI(title="Governor-MCP Backend")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

policy_engine = PolicyEngine()

# Initialize DB on startup
@app.on_event("startup")
def startup_event():
    init_db()

# --- API Endpoints for React Frontend ---

@app.get("/api/requests")
async def get_requests():
    """Fetch all requests from the database."""
    conn = get_connection()
    # Read as dicts
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM requests ORDER BY timestamp DESC LIMIT 1000")
    rows = cursor.fetchall()
    conn.close()
    return rows

@app.get("/api/stats")
async def get_stats():
    """Fetch global statistics from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM requests")
    total_requests = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM requests WHERE status='PENDING'")
    total_pending = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM requests WHERE status='BLOCKED'")
    total_blocked = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_requests": total_requests,
        "total_pending": total_pending,
        "total_blocked": total_blocked
    }

@app.post("/api/approve/{request_id}")
async def approve_request(request_id: str):
    """Approve a pending request."""
    update_status(request_id, "APPROVED")
    return {"status": "success", "message": f"Request {request_id} approved"}

@app.post("/api/deny/{request_id}")
async def deny_request(request_id: str):
    """Deny a pending request."""
    update_status(request_id, "DENIED")
    return {"status": "success", "message": f"Request {request_id} denied"}

@app.post("/api/reset")
async def reset_db():
    """Reset the database by deleting all requests."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM requests")
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Database reset successfully"}

# --- MCP Execution Endpoint ---

@app.post("/mcp/execute")
async def execute_tool(call: ToolCall):
    decision = policy_engine.evaluate(call.tool_name, call.args)

    if decision.action == "BLOCK":
        # Log as BLOCKED
        log_request(
            call.tool_name, 
            call.args, 
            "BLOCKED", 
            decision.reason, 
            decision.risk_level,
            call.agent_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=f"Blocked by policy: {decision.reason}"
        )

    elif decision.action == "REVIEW":
        # Log as PENDING
        request_id = log_request(
            call.tool_name, 
            call.args, 
            "PENDING", 
            decision.reason, 
            decision.risk_level,
            call.agent_id
        )
        
        # Enter Async Loop (HITL)
        start_time = time.time()
        timeout = 60 # seconds
        
        while time.time() - start_time < timeout:
            current_status = get_request_status(request_id)
            
            if current_status == "APPROVED":
                # Proceed to execution
                return {"status": "success", "data": f"Executed {call.tool_name}", "request_id": request_id}
            
            elif current_status == "DENIED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Request denied by human administrator."
                )
            
            await asyncio.sleep(1) # Poll every 1 second
            
        # Timeout occurred
        update_status(request_id, "TIMEOUT")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT, 
            detail="Request timed out waiting for approval."
        )

    else: # ALLOW
        # Log as COMPLETED
        log_request(
            call.tool_name, 
            call.args, 
            "COMPLETED", 
            decision.reason, 
            decision.risk_level,
            call.agent_id
        )
        return {"status": "success", "data": f"Executed {call.tool_name}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
