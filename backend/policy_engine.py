import fnmatch
import os
from typing import Any, Dict, List

import yaml

from .models import (
    AccessControlConfig,
    AccessPolicy,
    AgentPrincipal,
    FunctionResource,
    PolicyDecision,
    PolicyStatement,
)


class PolicyEngine:
    def __init__(self, policy_path: str = "policy.yaml"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.policy_path = os.path.join(base_dir, policy_path)
        self._policy_mtime: float | None = None
        self.access_control = self._load_policy()

    def _load_policy(self) -> AccessControlConfig:
        if not os.path.exists(self.policy_path):
            self._policy_mtime = None
            return AccessControlConfig()

        self._policy_mtime = os.path.getmtime(self.policy_path)

        with open(self.policy_path, "r") as f:
            data = yaml.safe_load(f) or {}

        # New IAM-style schema support
        if isinstance(data, dict) and "access_control" in data:
            return self._parse_access_control(data.get("access_control") or {})

        # Backward-compatible bootstrap from legacy rules
        if isinstance(data, dict) and "rules" in data:
            return self._convert_legacy_rules(data.get("rules") or [])

        return AccessControlConfig()

    def _parse_access_control(self, data: Dict[str, Any]) -> AccessControlConfig:
        functions = self._parse_functions(data.get("functions") or [])
        policies = self._parse_policies(data.get("policies") or [])
        agents = self._parse_agents(data.get("agents") or [])

        return AccessControlConfig(
            version=str(data.get("version") or "2026-02-01"),
            default_effect="DENY",
            agents=agents,
            functions=functions,
            policies=policies,
        )

    def _parse_functions(self, raw_functions: Any) -> Dict[str, FunctionResource]:
        parsed: Dict[str, FunctionResource] = {}

        if isinstance(raw_functions, dict):
            for function_id, definition in raw_functions.items():
                if not isinstance(definition, dict):
                    continue
                tool_name = str(definition.get("tool_name") or definition.get("tool") or function_id)
                parsed[str(function_id)] = FunctionResource(
                    id=str(function_id),
                    tool_name=tool_name,
                    description=definition.get("description"),
                )
            return parsed

        if isinstance(raw_functions, list):
            for item in raw_functions:
                if not isinstance(item, dict):
                    continue
                tool_name = str(item.get("tool_name") or item.get("tool") or "")
                function_id = str(item.get("id") or (f"tool:{tool_name}" if tool_name else ""))
                if not function_id or not tool_name:
                    continue
                parsed[function_id] = FunctionResource(
                    id=function_id,
                    tool_name=tool_name,
                    description=item.get("description"),
                )
        return parsed

    def _parse_policies(self, raw_policies: Any) -> Dict[str, AccessPolicy]:
        parsed: Dict[str, AccessPolicy] = {}

        if isinstance(raw_policies, dict):
            iterable = []
            for policy_id, definition in raw_policies.items():
                if isinstance(definition, dict):
                    definition = dict(definition)
                    definition["id"] = policy_id
                    iterable.append(definition)
        elif isinstance(raw_policies, list):
            iterable = [item for item in raw_policies if isinstance(item, dict)]
        else:
            iterable = []

        for item in iterable:
            policy_id = str(item.get("id") or "")
            if not policy_id:
                continue
            statements = self._parse_statements(item.get("statements") or [])
            parsed[policy_id] = AccessPolicy(
                id=policy_id,
                name=str(item.get("name") or policy_id),
                description=item.get("description"),
                statements=statements,
            )
        return parsed

    def _parse_statements(self, raw_statements: Any) -> List[PolicyStatement]:
        parsed: List[PolicyStatement] = []
        if not isinstance(raw_statements, list):
            return parsed

        for index, statement in enumerate(raw_statements):
            if not isinstance(statement, dict):
                continue
            effect = str(statement.get("effect") or "ALLOW").upper()
            if effect == "BLOCK":
                effect = "DENY"
            if effect not in {"ALLOW", "DENY", "REVIEW"}:
                continue

            actions = statement.get("actions") or ["invoke"]
            if isinstance(actions, str):
                actions = [actions]
            actions = [str(action).strip().lower() for action in actions if str(action).strip()]
            if not actions:
                actions = ["invoke"]

            resources = statement.get("resources")
            if resources is None and statement.get("tool"):
                resources = [f"tool:{statement.get('tool')}"]
            if isinstance(resources, str):
                resources = [resources]
            resources = [str(resource).strip() for resource in (resources or []) if str(resource).strip()]
            if not resources:
                continue

            parsed.append(
                PolicyStatement(
                    sid=str(statement.get("sid") or f"stmt-{index + 1}"),
                    effect=effect,
                    actions=actions,
                    resources=resources,
                    condition=statement.get("condition"),
                    risk_level=str(statement.get("risk_level") or statement.get("risk") or "low"),
                    description=statement.get("description"),
                )
            )
        return parsed

    def _parse_agents(self, raw_agents: Any) -> Dict[str, AgentPrincipal]:
        parsed: Dict[str, AgentPrincipal] = {}

        if isinstance(raw_agents, dict):
            iterable = []
            for agent_id, definition in raw_agents.items():
                if isinstance(definition, dict):
                    definition = dict(definition)
                    definition["id"] = agent_id
                    iterable.append(definition)
        elif isinstance(raw_agents, list):
            iterable = [item for item in raw_agents if isinstance(item, dict)]
        else:
            iterable = []

        for item in iterable:
            agent_id = str(item.get("id") or "")
            if not agent_id:
                continue
            attached = item.get("attached_policies") or item.get("policies") or []
            if isinstance(attached, str):
                attached = [attached]
            attached = [str(policy_id) for policy_id in attached if str(policy_id).strip()]
            parsed[agent_id] = AgentPrincipal(
                id=agent_id,
                name=item.get("name"),
                attached_policies=attached,
            )
        return parsed

    def _convert_legacy_rules(self, rules: List[Dict[str, Any]]) -> AccessControlConfig:
        function_resources: Dict[str, FunctionResource] = {}
        allow_statements: List[PolicyStatement] = []
        guardrail_statements: List[PolicyStatement] = []

        for index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                continue
            tool_name = str(rule.get("tool") or "").strip()
            if not tool_name:
                continue

            function_id = f"tool:{tool_name}"
            function_resources[function_id] = FunctionResource(id=function_id, tool_name=tool_name)

            action = str(rule.get("action") or "ALLOW").upper()
            effect = {"ALLOW": "ALLOW", "BLOCK": "DENY", "REVIEW": "REVIEW"}.get(action)
            if not effect:
                continue

            statement = PolicyStatement(
                sid=f"legacy-{index + 1}-{tool_name}-{effect.lower()}",
                effect=effect,
                actions=["invoke"],
                resources=[function_id],
                condition=rule.get("condition"),
                risk_level=str(rule.get("risk") or "low"),
                description="Auto-generated from legacy policy.yaml rules",
            )

            if effect == "ALLOW":
                allow_statements.append(statement)
            else:
                guardrail_statements.append(statement)

        policies: Dict[str, AccessPolicy] = {}
        attached_policy_ids: List[str] = []

        if guardrail_statements:
            guardrail_id = "legacy-global-guardrails"
            policies[guardrail_id] = AccessPolicy(
                id=guardrail_id,
                name="Legacy Global Guardrails",
                description="Converted from legacy REVIEW/BLOCK rules",
                statements=guardrail_statements,
            )
            attached_policy_ids.append(guardrail_id)

        if allow_statements:
            allow_id = "legacy-global-allowlist"
            policies[allow_id] = AccessPolicy(
                id=allow_id,
                name="Legacy Global Allowlist",
                description="Converted from legacy ALLOW rules",
                statements=allow_statements,
            )
            attached_policy_ids.append(allow_id)

        # Wildcard principal applies to all agents as onboarding baseline.
        agents = {
            "*": AgentPrincipal(
                id="*",
                name="All Agents (Legacy Baseline)",
                attached_policies=attached_policy_ids,
            )
        }

        return AccessControlConfig(
            version="2026-legacy-bootstrap",
            default_effect="DENY",
            agents=agents,
            functions=function_resources,
            policies=policies,
        )

    def evaluate(self, tool_name: str, args: Dict[str, Any], agent_id: str = "Unknown") -> PolicyDecision:
        self._refresh_if_needed()
        action = "invoke"
        resource_id = self._tool_to_resource(tool_name)
        principal_ids = [agent_id]
        if "*" not in principal_ids:
            principal_ids.append("*")

        matched_allows: List[Dict[str, Any]] = []
        matched_reviews: List[Dict[str, Any]] = []
        matched_denies: List[Dict[str, Any]] = []

        for principal_id in principal_ids:
            principal = self.access_control.agents.get(principal_id)
            if not principal:
                continue

            for policy_id in principal.attached_policies:
                policy = self.access_control.policies.get(policy_id)
                if not policy:
                    continue

                for statement in policy.statements:
                    if not self._statement_matches(statement, action, resource_id, tool_name, args):
                        continue

                    match_data = {
                        "policy_id": policy_id,
                        "statement_id": statement.sid,
                        "risk_level": statement.risk_level,
                        "condition": statement.condition,
                    }
                    if statement.effect == "DENY":
                        matched_denies.append(match_data)
                    elif statement.effect == "REVIEW":
                        matched_reviews.append(match_data)
                    elif statement.effect == "ALLOW":
                        matched_allows.append(match_data)

        if matched_denies:
            return self._decision_from_matches("BLOCK", matched_denies, "Explicit deny matched")
        if matched_reviews:
            return self._decision_from_matches("REVIEW", matched_reviews, "Human review required")
        if matched_allows:
            return self._decision_from_matches("ALLOW", matched_allows, "Explicit allow matched")

        return PolicyDecision(
            action="BLOCK",
            risk_level="high",
            reason=f"Default deny: no allow policy for agent '{agent_id}' on '{tool_name}'",
        )

    def get_access_view(self) -> Dict[str, Any]:
        self._refresh_if_needed()
        access_model = self.access_control.model_dump()
        agent_matrix: List[Dict[str, Any]] = []

        for agent_id, principal in sorted(self.access_control.agents.items(), key=lambda item: item[0]):
            statements: List[Dict[str, Any]] = []
            for policy_id in principal.attached_policies:
                policy = self.access_control.policies.get(policy_id)
                if not policy:
                    continue
                for statement in policy.statements:
                    statements.append(
                        {
                            "policy_id": policy_id,
                            "policy_name": policy.name,
                            "statement_id": statement.sid,
                            "effect": statement.effect,
                            "actions": statement.actions,
                            "resources": statement.resources,
                            "condition": statement.condition,
                            "risk_level": statement.risk_level,
                        }
                    )

            agent_matrix.append(
                {
                    "id": principal.id,
                    "name": principal.name,
                    "attached_policies": principal.attached_policies,
                    "statements": statements,
                }
            )

        return {
            "default_effect": self.access_control.default_effect,
            "version": self.access_control.version,
            "functions": sorted(access_model.get("functions", {}).values(), key=lambda item: item.get("id", "")),
            "policies": sorted(access_model.get("policies", {}).values(), key=lambda item: item.get("id", "")),
            "agents": agent_matrix,
        }

    def create_policy(self, policy_id: str, name: str, description: str | None = None) -> AccessPolicy:
        self._refresh_if_needed()
        normalized_id = policy_id.strip()
        if not normalized_id:
            raise ValueError("policy_id is required")
        if normalized_id in self.access_control.policies:
            raise ValueError(f"Policy '{normalized_id}' already exists")

        policy = AccessPolicy(
            id=normalized_id,
            name=name.strip() or normalized_id,
            description=description,
            statements=[],
        )
        self.access_control.policies[normalized_id] = policy
        self._save_policy()
        return policy

    def remove_policy(self, policy_id: str) -> int:
        self._refresh_if_needed()
        normalized_policy_id = policy_id.strip()
        if not normalized_policy_id:
            raise ValueError("policy_id is required")
        if normalized_policy_id not in self.access_control.policies:
            raise ValueError(f"Unknown policy '{normalized_policy_id}'")

        del self.access_control.policies[normalized_policy_id]

        detached_agents = 0
        for principal in self.access_control.agents.values():
            if normalized_policy_id not in principal.attached_policies:
                continue
            principal.attached_policies = [
                attached_id
                for attached_id in principal.attached_policies
                if attached_id != normalized_policy_id
            ]
            detached_agents += 1

        self._save_policy()
        return detached_agents

    def add_statement(
        self,
        policy_id: str,
        effect: str,
        resources: List[str],
        actions: List[str] | None = None,
        condition: str | None = None,
        risk_level: str = "low",
        description: str | None = None,
        sid: str | None = None,
    ) -> PolicyStatement:
        self._refresh_if_needed()
        policy = self.access_control.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Unknown policy '{policy_id}'")

        normalized_effect = effect.upper()
        if normalized_effect == "BLOCK":
            normalized_effect = "DENY"
        if normalized_effect not in {"ALLOW", "DENY", "REVIEW"}:
            raise ValueError("effect must be one of ALLOW, DENY, REVIEW")

        normalized_resources = [resource.strip() for resource in resources if resource and resource.strip()]
        if not normalized_resources:
            raise ValueError("At least one resource is required")

        normalized_actions = [action.strip().lower() for action in (actions or ["invoke"]) if action and action.strip()]
        if not normalized_actions:
            normalized_actions = ["invoke"]

        statement_id = (sid or "").strip() or self._generate_statement_id(policy)
        if any(statement.sid == statement_id for statement in policy.statements):
            raise ValueError(f"Statement id '{statement_id}' already exists in policy '{policy_id}'")

        statement = PolicyStatement(
            sid=statement_id,
            effect=normalized_effect,
            actions=normalized_actions,
            resources=normalized_resources,
            condition=condition or None,
            risk_level=risk_level or "low",
            description=description,
        )
        policy.statements.append(statement)

        for resource in normalized_resources:
            if resource.startswith("tool:") and resource not in self.access_control.functions:
                tool_name = resource.replace("tool:", "", 1)
                self.access_control.functions[resource] = FunctionResource(id=resource, tool_name=tool_name)

        self._save_policy()
        return statement

    def remove_statement(self, policy_id: str, statement_id: str) -> None:
        self._refresh_if_needed()
        policy = self.access_control.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Unknown policy '{policy_id}'")

        original_count = len(policy.statements)
        policy.statements = [statement for statement in policy.statements if statement.sid != statement_id]
        if len(policy.statements) == original_count:
            raise ValueError(f"Statement '{statement_id}' was not found in policy '{policy_id}'")

        self._save_policy()

    def attach_policy_to_agent(self, agent_id: str, policy_id: str, agent_name: str | None = None) -> AgentPrincipal:
        self._refresh_if_needed()
        normalized_agent_id = agent_id.strip()
        if not normalized_agent_id:
            raise ValueError("agent_id is required")
        if policy_id not in self.access_control.policies:
            raise ValueError(f"Unknown policy '{policy_id}'")

        principal = self.access_control.agents.get(normalized_agent_id)
        if not principal:
            principal = AgentPrincipal(id=normalized_agent_id, name=agent_name or None, attached_policies=[])
            self.access_control.agents[normalized_agent_id] = principal

        if agent_name and not principal.name:
            principal.name = agent_name

        if policy_id not in principal.attached_policies:
            principal.attached_policies.append(policy_id)

        self._save_policy()
        return principal

    def detach_policy_from_agent(self, agent_id: str, policy_id: str) -> AgentPrincipal:
        self._refresh_if_needed()
        principal = self.access_control.agents.get(agent_id)
        if not principal:
            raise ValueError(f"Unknown agent '{agent_id}'")
        if policy_id not in principal.attached_policies:
            raise ValueError(f"Policy '{policy_id}' is not attached to agent '{agent_id}'")

        principal.attached_policies = [item for item in principal.attached_policies if item != policy_id]
        self._save_policy()
        return principal

    def remove_agent(self, agent_id: str) -> None:
        self._refresh_if_needed()
        normalized_agent_id = agent_id.strip()
        if not normalized_agent_id:
            raise ValueError("agent_id is required")
        if normalized_agent_id == "*":
            raise ValueError("The wildcard baseline agent '*' cannot be removed")
        if normalized_agent_id not in self.access_control.agents:
            raise ValueError(f"Unknown agent '{normalized_agent_id}'")

        del self.access_control.agents[normalized_agent_id]
        self._save_policy()

    def _generate_statement_id(self, policy: AccessPolicy) -> str:
        base = f"{policy.id}-stmt"
        existing = {statement.sid for statement in policy.statements}
        index = 1
        candidate = f"{base}-{index}"
        while candidate in existing:
            index += 1
            candidate = f"{base}-{index}"
        return candidate

    def _refresh_if_needed(self) -> None:
        if not os.path.exists(self.policy_path):
            return

        current_mtime = os.path.getmtime(self.policy_path)
        if self._policy_mtime is None or current_mtime > self._policy_mtime:
            self.access_control = self._load_policy()

    def _save_policy(self) -> None:
        serialized = self._serialize_access_control()
        with open(self.policy_path, "w") as f:
            yaml.safe_dump(serialized, f, sort_keys=False)
        self._policy_mtime = os.path.getmtime(self.policy_path)

    def _serialize_access_control(self) -> Dict[str, Any]:
        functions = [
            function.model_dump()
            for _, function in sorted(self.access_control.functions.items(), key=lambda item: item[0])
        ]
        policies = []
        for _, policy in sorted(self.access_control.policies.items(), key=lambda item: item[0]):
            policy_data = {
                "id": policy.id,
                "name": policy.name,
                "statements": [statement.model_dump() for statement in policy.statements],
            }
            if policy.description:
                policy_data["description"] = policy.description
            policies.append(policy_data)

        agents = []
        for _, principal in sorted(self.access_control.agents.items(), key=lambda item: item[0]):
            agent_data = {
                "id": principal.id,
                "policies": principal.attached_policies,
            }
            if principal.name:
                agent_data["name"] = principal.name
            agents.append(agent_data)

        return {
            "access_control": {
                "version": self.access_control.version,
                "default_effect": self.access_control.default_effect,
                "functions": functions,
                "policies": policies,
                "agents": agents,
            }
        }

    def _decision_from_matches(self, action: str, matches: List[Dict[str, Any]], reason_prefix: str) -> PolicyDecision:
        first = matches[0]
        return PolicyDecision(
            action=action,
            risk_level=first.get("risk_level", "low"),
            reason=f"{reason_prefix}: {first.get('policy_id')}::{first.get('statement_id')}",
            matched_policy_ids=[match["policy_id"] for match in matches],
            matched_statement_ids=[match["statement_id"] for match in matches],
        )

    def _statement_matches(
        self,
        statement: PolicyStatement,
        action: str,
        resource_id: str,
        tool_name: str,
        args: Dict[str, Any],
    ) -> bool:
        if not self._match_any(action.lower(), [value.lower() for value in statement.actions]):
            return False

        resource_candidates = [resource_id, tool_name]
        if not any(self._match_any(candidate, statement.resources) for candidate in resource_candidates):
            return False

        if statement.condition and not self._check_condition(statement.condition, args):
            return False
        return True

    def _match_any(self, value: str, patterns: List[str]) -> bool:
        for pattern in patterns:
            normalized = pattern.strip()
            if not normalized:
                continue
            if fnmatch.fnmatch(value, normalized):
                return True
        return False

    def _tool_to_resource(self, tool_name: str) -> str:
        return f"tool:{tool_name}"

    def _check_condition(self, condition: str, args: Dict[str, Any]) -> bool:
        # Supports expressions in the shape: "param contains 'value'"
        parts = condition.split(" ")
        if len(parts) < 3 or parts[1] != "contains" or "'" not in condition:
            return False

        key = parts[0]
        values = condition.split("'")
        if len(values) < 2:
            return False
        value_to_check = values[1]

        arg_value = args.get(key)
        return arg_value is not None and value_to_check in str(arg_value)
