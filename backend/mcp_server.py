
import sys
import os
import asyncio
import time
from mcp.server.fastmcp import FastMCP
from typing import Optional

# Add project root to sys.path to allow imports from shared/backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.policy_engine import PolicyEngine
from shared.db import log_request, update_status, get_request_status, init_db

# Initialize Policy Engine
policy_engine = PolicyEngine()

# Initialize FastMCP Server
mcp = FastMCP("Governor MCP Server")

# Helper function for Policy Enforcement
async def enforce_policy(tool_name: str, args: dict, agent_id: str = "Unknown"):
    decision = policy_engine.evaluate(tool_name, args)

    if decision.action == "BLOCK":
        log_request(tool_name, args, "BLOCKED", decision.reason, decision.risk_level, agent_id)
        raise ValueError(f"BLOCKED: {decision.reason}")

    elif decision.action == "REVIEW":
        request_id = log_request(tool_name, args, "PENDING", decision.reason, decision.risk_level, agent_id)
        print(f"Request {request_id} pending approval for {tool_name}...")
        
        # Poll for approval
        start_time = time.time()
        timeout = 60
        
        while time.time() - start_time < timeout:
            status = get_request_status(request_id)
            if status == "APPROVED":
                return True
            elif status == "DENIED":
                raise ValueError("Request DENIED by administrator.")
            await asyncio.sleep(1)
            
        update_status(request_id, "TIMEOUT")
        raise TimeoutError("Request timed out waiting for approval.")

    else: # ALLOW
        log_request(tool_name, args, "COMPLETED", decision.reason, decision.risk_level, agent_id)
        return True

# --- Tools ---

@mcp.tool()
async def read_file(path: str) -> str:
    """Read contents of a file."""
    await enforce_policy("read_file", {"path": path})
    try:
        # For demo purposes, we can actually read the file if it exists and is safe?
        # Or just return a mock content for safety in this demo environment.
        # Let's try to actually read if it's safe-ish, otherwise mock.
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read()
        return f"Mock content of {path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.tool()
async def get_weather(city: str) -> str:
    """Get weather for a city."""
    await enforce_policy("get_weather", {"city": city})
    return f"Weather in {city}: Sunny, 25°C"

@mcp.tool()
async def network_scan(target: str) -> str:
    """Scan a network target."""
    await enforce_policy("network_scan", {"target": target})
    return f"Scan results for {target}: Open ports: 80, 443"

@mcp.tool()
async def delete_database(db_name: str) -> str:
    """Delete a database (Dangerous!)."""
    await enforce_policy("delete_database", {"db_name": db_name})
    return f"Database {db_name} deleted successfully."

@mcp.tool()
async def deploy_contract(contract_id: str) -> str:
    """Deploy a smart contract."""
    await enforce_policy("deploy_contract", {"contract_id": contract_id})
    return f"Contract {contract_id} deployed to mainnet."

@mcp.tool()
async def grant_access(user: str, level: str) -> str:
    """Grant access level to a user."""
    await enforce_policy("grant_access", {"user": user, "level": level})
    return f"User {user} granted {level} access."

@mcp.tool()
async def access_aws_keys(service: str) -> str:
    """Access AWS keys for a service."""
    await enforce_policy("access_aws_keys", {"service": service})
    return f"AWS keys for {service}: AKIA..."

if __name__ == "__main__":
    # Initialize DB (safe to call multiple times)
    init_db()
    mcp.run()
