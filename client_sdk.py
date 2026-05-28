from aegis_aip import AegisClient

print("--- AI AGENT BOOTING UP ---")

# 1. Initialize the Interceptor SDK
# This automatically fetches the token and configures the Sidecar route.
aegis = AegisClient(
    agent_id="RefundBot-001",
    control_plane_url="https://aegis-live-node.onrender.com",
    sidecar_url="http://localhost:8080"
)

# 2. THE GOOD ACTION 
print("\n>>> ACTION 1: Agent attempting a normal $50 refund...")
res1 = aegis.secure_tool_call(
    tool_name="stripe:refund:write",
    params={"customer": "user_992", "amount": 50}
)
print(f"Proxy Decision: {res1}")

# 3. THE CONTEXTUAL HALLUCINATION
print("\n>>> ACTION 2: Agent hallucinating... attempting to refund $50,000!")
res2 = aegis.secure_tool_call(
    tool_name="stripe:refund:write",
    params={"customer": "user_992", "amount": 50000}
)
print(f"Proxy Decision: {res2}")