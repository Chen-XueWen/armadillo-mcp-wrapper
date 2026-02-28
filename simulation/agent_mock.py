import requests
import time
import json
import random
import sys

BASE_URL = "http://localhost:8000/mcp/execute"

TOOLS = [
    # Safe
    ("read_file", {"path": "/var/log/app.log"}),
    ("read_file", {"path": "/home/user/notes.txt"}),
    ("get_weather", {"city": "Singapore"}),
    ("get_weather", {"city": "London"}),
    ("translate_text", {"text": "Hello world", "target": "es"}),
    ("network_scan", {"target": "192.168.1.10"}),
    
    # Blocked
    ("read_file", {"path": "/etc/shadow"}),
    ("read_file", {"path": "/app/.env"}),
    ("network_scan", {"target": "fin_server_internal"}),

    # Review (HITL)
    ("delete_database", {"db_name": "users_prod"}),
    ("deploy_contract", {"contract_id": "0x123...abc"}),
    ("grant_access", {"user": "unknown_actor", "level": "admin"}),
    ("access_aws_keys", {"service": "s3_buckets"}),
]

AGENTS = [
    "security-bot-01",
    "devops-pipeline-prod",
    "payment-service-v2",
    "audit-crawler",
    "user-dashboard-bff",
    "legacy-sync-job"
]

def send_request(tool_name, args):
    agent = random.choice(AGENTS)
    try:
        response = requests.post(BASE_URL, json={"tool_name": tool_name, "args": args, "agent_id": agent}, timeout=2)
        status_code = response.status_code
        if status_code == 200:
            print(f"✅ [200] {agent} -> {tool_name}")
        elif status_code == 403:
            print(f"🛡️ [403] {agent} -> {tool_name} BLOCKED")
        elif status_code == 408:
             print(f"⏱️ [408] {agent} -> {tool_name} TIMEOUT")
        else:
            print(f"⚠️ [{status_code}] {agent} -> {tool_name}")
    except Exception as e:
        print(f"❌ Error: {e}")

def run_chaos_mode():
    print("🚀 Starting Chaos Mode (Continuous Traffic)...")
    print("Press Ctrl+C to stop.")
    
    while True:
        tool, args = random.choice(TOOLS)
        
        # Introduce some burstiness
        delay = random.uniform(0.1, 1.5) 
        time.sleep(delay)
        
        # Determine if we should spam a bit (burst)
        if random.random() < 0.1:
            print("🔥 BURST TRAFFIC DETECTED!")
            for _ in range(5):
                 t_burst, a_burst = random.choice(TOOLS)
                 send_request(t_burst, a_burst)
                 time.sleep(0.1)
        
        send_request(tool, args)

if __name__ == "__main__":
    # Wait for service to start
    time.sleep(2)
    run_chaos_mode()
