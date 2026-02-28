import yaml
import os
from typing import Dict, Any, List
from .models import PolicyDecision

class PolicyEngine:
    def __init__(self, policy_path: str = "policy.yaml"):
        # Resolve policy path relative to the project root
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.policy_path = os.path.join(base_dir, policy_path)
        self.rules = self._load_policy()

    def _load_policy(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.policy_path):
            return []
        with open(self.policy_path, "r") as f:
            data = yaml.safe_load(f)
            return data.get("rules", [])

    def evaluate(self, tool_name: str, args: Dict[str, Any]) -> PolicyDecision:
        # Default decision if no rules match
        decision = PolicyDecision(action="ALLOW", risk_level="low", reason="Default allow")

        for rule in self.rules:
            if rule.get("tool") != tool_name:
                continue
            
            # Check condition if present
            condition = rule.get("condition")
            if condition:
                if not self._check_condition(condition, args):
                    continue
            
            # Match found
            return PolicyDecision(
                action=rule.get("action", "ALLOW"),
                risk_level=rule.get("risk", "low"),
                reason=f"Matched rule for {tool_name}" + (f" with condition: {condition}" if condition else "")
            )
        
        return decision

    def _check_condition(self, condition: str, args: Dict[str, Any]) -> bool:
        # Simple condition parser for PoC
        # Supporting: "param contains 'value'"
        parts = condition.split(" ")
        if len(parts) >= 3 and parts[1] == "contains":
            key = parts[0]
            value_to_check = condition.split("'")[1] # Extract value between single quotes
            
            arg_value = args.get(key)
            if arg_value and value_to_check in str(arg_value):
                return True
        return False
