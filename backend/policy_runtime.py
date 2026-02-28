import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.policy_engine import PolicyEngine
from shared.db import get_request_status, log_request, update_status

REVIEW_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 1


class PolicyEnforcementError(Exception):
    """Base class for policy-enforcement errors."""


class PolicyBlockedError(PolicyEnforcementError):
    """Raised when a request is blocked by policy."""


class PolicyDeniedError(PolicyEnforcementError):
    """Raised when a human reviewer denies the request."""


class PolicyTimeoutError(PolicyEnforcementError):
    """Raised when a review request times out."""


@dataclass
class PolicyEnforcementResult:
    status: str
    request_id: Optional[str] = None


async def enforce_policy(
    policy_engine: PolicyEngine,
    tool_name: str,
    args: Dict[str, Any],
    agent_id: str = "Unknown",
    timeout_seconds: int = REVIEW_TIMEOUT_SECONDS,
    auto_complete_allow: bool = True,
) -> PolicyEnforcementResult:
    decision = policy_engine.evaluate(tool_name, args, agent_id)

    if decision.action == "BLOCK":
        log_request(tool_name, args, "BLOCKED", decision.reason, decision.risk_level, agent_id)
        raise PolicyBlockedError(decision.reason or "Blocked by policy")

    if decision.action == "ALLOW":
        allow_status = "COMPLETED" if auto_complete_allow else "APPROVED"
        request_id = log_request(tool_name, args, allow_status, decision.reason, decision.risk_level, agent_id)
        return PolicyEnforcementResult(status=allow_status, request_id=request_id)

    request_id = log_request(tool_name, args, "PENDING", decision.reason, decision.risk_level, agent_id)

    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        current_status = get_request_status(request_id)
        if current_status == "APPROVED":
            return PolicyEnforcementResult(status="APPROVED", request_id=request_id)
        if current_status == "DENIED":
            raise PolicyDeniedError("Request denied by human administrator.")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

    update_status(request_id, "TIMEOUT")
    raise PolicyTimeoutError("Request timed out waiting for approval.")


def finalize_request_status(request_id: Optional[str], status: str) -> None:
    if not request_id:
        return
    update_status(request_id, status)
