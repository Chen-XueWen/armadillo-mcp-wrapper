from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

class ToolCall(BaseModel):
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    agent_id: str = "Unknown"

class PolicyStatement(BaseModel):
    sid: str
    effect: Literal["ALLOW", "DENY", "REVIEW"]
    actions: List[str] = Field(default_factory=lambda: ["invoke"])
    resources: List[str] = Field(default_factory=list)
    condition: Optional[str] = None
    risk_level: str = "low"
    description: Optional[str] = None

class AccessPolicy(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    statements: List[PolicyStatement] = Field(default_factory=list)

class AgentPrincipal(BaseModel):
    id: str
    name: Optional[str] = None
    attached_policies: List[str] = Field(default_factory=list)

class FunctionResource(BaseModel):
    id: str
    tool_name: str
    description: Optional[str] = None

class AccessControlConfig(BaseModel):
    version: str = "2026-02-01"
    default_effect: Literal["DENY"] = "DENY"
    agents: Dict[str, AgentPrincipal] = Field(default_factory=dict)
    functions: Dict[str, FunctionResource] = Field(default_factory=dict)
    policies: Dict[str, AccessPolicy] = Field(default_factory=dict)

class PolicyDecision(BaseModel):
    action: str  # ALLOW, BLOCK, REVIEW
    risk_level: str
    reason: Optional[str] = None
    matched_policy_ids: List[str] = Field(default_factory=list)
    matched_statement_ids: List[str] = Field(default_factory=list)

class CreatePolicyRequest(BaseModel):
    policy_id: str
    name: str
    description: Optional[str] = None

class AddStatementRequest(BaseModel):
    policy_id: str
    effect: Literal["ALLOW", "DENY", "REVIEW", "BLOCK"]
    resources: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=lambda: ["invoke"])
    condition: Optional[str] = None
    risk_level: str = "low"
    description: Optional[str] = None
    sid: Optional[str] = None

class PolicyAttachmentRequest(BaseModel):
    agent_id: str
    policy_id: str
    agent_name: Optional[str] = None

class RemoveAgentRequest(BaseModel):
    agent_id: str
