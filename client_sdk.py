import requests

print("--- AI AGENT BOOTING UP ---")

# 1. The "Dumb" Request
# We are ONLY sending the Agent ID. The agent doesn't dictate its rules anymore.
payload = {
    "agent_id": "RefundBot-001" 
}
print("Requesting ID Badge from Aegis Control Plane...")
response = requests.post("https://aegis-live-node.onrender.com/mint", json=payload)

if response.status_code != 200:
    print(f"[FATAL ERROR] Aegis rejected our identity: {response.text}")
    exit()

envelope = response.json()["ibct_envelope"]
print(f"[SYSTEM] Envelope secured! The Control Plane has injected our database policies.\n")

# 2. THE GOOD ACTION 
print(">>> ACTION 1: Agent attempting a normal $50 refund...")
good_request = {
    "envelope": envelope,
    "tool_name": "refund",
    "action_params": {"customer": "user_992", "amount": 50}
}
res1 = requests.post("https://aegis-live-node.onrender.com/execute", json=good_request)
print(f"Proxy: {res1.json()}\n")

# 3. THE CONTEXTUAL HALLUCINATION
print(">>> ACTION 2: Agent hallucinating... attempting to refund $50,000!")
hallucination_request = {
    "envelope": envelope,
    "tool_name": "refund",
    "action_params": {"customer": "user_992", "amount": 50000}
}
res2 = requests.post("https://aegis-live-node.onrender.com/execute", json=hallucination_request)
print(f"Proxy: {res2.json()}\n")