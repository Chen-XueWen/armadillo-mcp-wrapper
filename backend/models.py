from pydantic import BaseModel
from typing import Dict, Any, Optional

class ToolCall(BaseModel):
    tool_name: str
    args: Dict[str, Any]
    agent_id: str = "Unknown"

class PolicyDecision(BaseModel):
    action: str  # ALLOW, BLOCK, REVIEW
    risk_level: str
    reason: Optional[str] = None
