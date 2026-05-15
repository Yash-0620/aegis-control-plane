# 🛡️ Aegis-AIP: The Agentic Identity Protocol

**Stop hardcoding god-mode API keys into your AI agents.** Aegis is the open-source implementation of the Agent Identity Protocol (AIP). It provides zero-trust, cryptographic identity and parameter-bounding for your AI agents interacting with Model Context Protocol (MCP) servers.

If your LLM hallucinates and tries to drop a database or refund $50,000, Aegis catches it at the network layer.

## 🚀 5-Minute Quickstart

### 1. Install the SDK
```bash
pip install aegis-aip
```

### 2. Secure Your Agent
Wrap your existing tool calls in the Aegis Client. It automatically fetches a dynamic, 5-minute IBCT (Invocation-Bound Capability Token) and mathematically bounds the agent's blast radius.

```python
from aegis_aip import AegisClient

# 1. Initialize the client with your Agent ID and your Aegis Control Plane URL
aegis = AegisClient(
    agent_id="RefundBot-001", 
    control_plane_url="[https://aegis-live-node.onrender.com](https://aegis-live-node.onrender.com)"
)

# 2. When your LLM decides to use a tool, route it securely through Aegis
response = aegis.secure_tool_call(
    tool_name="refund",
    action_params={"customer": "user_992", "amount": 50}
)

print(response)
```

### Why Aegis?
* **Zero-Trust MCP Routing:** Secures Anthropic's Model Context Protocol.
* **Deterministic Parameter Bounding:** Blocks contextual hallucinations mathematically.
* **Audit-Ready:** Generates cryptographic lineage logs for compliance (SOC2/NYDFS).