import os
import sys
from typing import Dict, List

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# Add project root to sys.path to allow imports from shared.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import (  # noqa: E402
    AddStatementRequest,
    CreatePolicyRequest,
    PolicyAttachmentRequest,
    RemoveAgentRequest,
    ToolCall,
)
from backend.policy_engine import PolicyEngine  # noqa: E402
from backend.policy_runtime import (  # noqa: E402
    PolicyBlockedError,
    PolicyDeniedError,
    PolicyTimeoutError,
    enforce_policy,
)
from shared.db import get_connection, init_db, update_status  # noqa: E402

DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
ADMIN_API_KEY = os.getenv("GOVERNOR_ADMIN_API_KEY", "").strip()


def _cors_origins_from_env() -> List[str]:
    raw = os.getenv("GOVERNOR_CORS_ORIGINS", "")
    parsed = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return parsed or DEFAULT_CORS_ORIGINS


def _row_factory(cursor, row) -> Dict[str, object]:
    return dict(zip([column[0] for column in cursor.description], row))


def require_admin_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not ADMIN_API_KEY:
        return
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid admin API key",
        )


app = FastAPI(title="Governor-MCP Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_from_env(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

policy_engine = PolicyEngine()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> Dict[str, str]:
    with get_connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ready"}


@app.get("/api/requests")
async def get_requests() -> List[Dict[str, object]]:
    with get_connection() as conn:
        conn.row_factory = _row_factory
        rows = conn.execute("SELECT * FROM requests ORDER BY timestamp DESC LIMIT 1000").fetchall()
    return rows


@app.get("/api/stats")
async def get_stats() -> Dict[str, int]:
    with get_connection() as conn:
        total_requests = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        total_pending = conn.execute("SELECT COUNT(*) FROM requests WHERE status='PENDING'").fetchone()[0]
        total_blocked = conn.execute("SELECT COUNT(*) FROM requests WHERE status='BLOCKED'").fetchone()[0]

    return {
        "total_requests": total_requests,
        "total_pending": total_pending,
        "total_blocked": total_blocked,
    }


@app.get("/api/access-control")
async def get_access_control() -> Dict[str, object]:
    return policy_engine.get_access_view()


@app.post("/api/access-control/policies")
async def create_policy(
    payload: CreatePolicyRequest,
    _: None = Depends(require_admin_api_key),
) -> Dict[str, object]:
    try:
        policy = policy_engine.create_policy(
            policy_id=payload.policy_id,
            name=payload.name,
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "status": "success",
        "policy": policy.model_dump(),
        "access_control": policy_engine.get_access_view(),
    }


@app.post("/api/access-control/statements")
async def add_statement(
    payload: AddStatementRequest,
    _: None = Depends(require_admin_api_key),
) -> Dict[str, object]:
    try:
        statement = policy_engine.add_statement(
            policy_id=payload.policy_id,
            effect=payload.effect,
            resources=payload.resources,
            actions=payload.actions,
            condition=payload.condition,
            risk_level=payload.risk_level,
            description=payload.description,
            sid=payload.sid,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "status": "success",
        "statement": statement.model_dump(),
        "access_control": policy_engine.get_access_view(),
    }


@app.delete("/api/access-control/policies/{policy_id}/statements/{statement_id}")
async def delete_statement(
    policy_id: str,
    statement_id: str,
    _: None = Depends(require_admin_api_key),
) -> Dict[str, object]:
    try:
        policy_engine.remove_statement(policy_id, statement_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "status": "success",
        "message": f"Deleted statement {statement_id}",
        "access_control": policy_engine.get_access_view(),
    }


@app.post("/api/access-control/agents/attach-policy")
async def attach_policy(
    payload: PolicyAttachmentRequest,
    _: None = Depends(require_admin_api_key),
) -> Dict[str, object]:
    try:
        principal = policy_engine.attach_policy_to_agent(
            agent_id=payload.agent_id,
            policy_id=payload.policy_id,
            agent_name=payload.agent_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "status": "success",
        "agent": principal.model_dump(),
        "access_control": policy_engine.get_access_view(),
    }


@app.post("/api/access-control/agents/detach-policy")
async def detach_policy(
    payload: PolicyAttachmentRequest,
    _: None = Depends(require_admin_api_key),
) -> Dict[str, object]:
    try:
        principal = policy_engine.detach_policy_from_agent(
            agent_id=payload.agent_id,
            policy_id=payload.policy_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "status": "success",
        "agent": principal.model_dump(),
        "access_control": policy_engine.get_access_view(),
    }


@app.post("/api/access-control/agents/remove")
async def remove_agent(
    payload: RemoveAgentRequest,
    _: None = Depends(require_admin_api_key),
) -> Dict[str, object]:
    try:
        policy_engine.remove_agent(payload.agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "status": "success",
        "message": f"Removed agent {payload.agent_id}",
        "access_control": policy_engine.get_access_view(),
    }


@app.post("/api/approve/{request_id}")
async def approve_request(
    request_id: str,
    _: None = Depends(require_admin_api_key),
) -> Dict[str, str]:
    update_status(request_id, "APPROVED")
    return {"status": "success", "message": f"Request {request_id} approved"}


@app.post("/api/deny/{request_id}")
async def deny_request(
    request_id: str,
    _: None = Depends(require_admin_api_key),
) -> Dict[str, str]:
    update_status(request_id, "DENIED")
    return {"status": "success", "message": f"Request {request_id} denied"}


@app.post("/api/reset")
async def reset_db(_: None = Depends(require_admin_api_key)) -> Dict[str, str]:
    with get_connection() as conn:
        conn.execute("DELETE FROM requests")
    return {"status": "success", "message": "Database reset successfully"}


@app.post("/mcp/execute")
async def execute_tool(call: ToolCall) -> Dict[str, object]:
    try:
        result = await enforce_policy(policy_engine, call.tool_name, call.args, call.agent_id)
    except PolicyBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Blocked by policy: {exc}",
        ) from exc
    except PolicyDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PolicyTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail=str(exc)) from exc

    response: Dict[str, object] = {"status": "success", "data": f"Executed {call.tool_name}"}
    if result.request_id:
        response["request_id"] = result.request_id
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
