# 🛡️ Aegis Protocol: Enterprise Control Plane

Welcome to the core infrastructure of the Agentic Identity Protocol (AIP). 

Aegis is the open-source standard for zero-trust AI agent security. It prevents autonomous AI agents (powered by LLMs like GPT-4, Claude, or Llama) from executing destructive actions (hallucinations, lateral escalation) when interacting with real-world enterprise infrastructure via the Model Context Protocol (MCP).

**The "Switzerland Moat" for Non-Human Identities (NHI).** Aegis Control Plane is a model-agnostic, zero-trust backend that manages the lifecycle of Invocation-Bound Capability Tokens (IBCTs) for AI Agents. It provides enterprise-grade IAM for the Model Context Protocol (MCP) without relying on brittle prompt engineering or LLM alignment.

## 🛡️ The Architecture: Ed25519 Cryptography
Unlike legacy API wrappers that require synchronous cloud round-trips to evaluate agent permissions, Aegis utilizes **Asymmetric Ed25519 Cryptography**:
1. **The Private Key (This Repo):** The Control Plane securely holds the Ed25519 Private Key. It is the only entity mathematically capable of minting IBCTs.
2. **The Public Key (The Edge):** The open-source `aegis-mcp-sidecar` holds the Public Key, allowing it to mathematically verify token signatures locally in `<2ms`.

This architecture decouples token issuance from token verification, granting AI agents true zero-latency execution while maintaining absolute cryptographic bounds.

## 🚀 Enterprise Compliance (SOC2 & NYDFS)
Aegis automatically ingests asynchronous telemetry from the edge proxies, creating an immutable SIEM (Security Information and Event Management) ledger in PostgreSQL. Every hallucination, blocked payload, and authorized tool call is forensically logged for strict regulatory compliance.

---

## 🛠️ Integration & Developer Friction

To keep integration frictionless, developers do **not** need to interact with the REST API directly. We provide a drop-in Python SDK (`aegis-aip`) that acts as a secure network interceptor.

### 1. Install the SDK
```bash
pip install aegis-aip
```

### 2. Secure Your Agent in 3 Lines
```python
from aegis_aip import AegisClient

# 1. Initialize the SDK (Automatically fetches IBCTs from the Control Plane)
aegis = AegisClient(
    agent_id="FinanceBot_live_8f45f0...",
    control_plane_url="[https://aegis-live-node.onrender.com](https://aegis-live-node.onrender.com)",
    sidecar_url="http://localhost:8080"
)

# 2. Wrap your MCP calls. Aegis handles the secure routing and auth headers.
response = aegis.secure_tool_call(
    tool_name="stripe:refund:write",
    params={"amount": 50, "transaction_id": "tx_123"}
)

print(response)
```

## 🏗️ Self-Hosting the Control Plane

If your enterprise requires an entirely on-premise, air-gapped deployment, you can self-host the Control Plane.

### Prerequisites
- Python 3.11+
- PostgreSQL Database (e.g., Supabase)

### Deployment Steps
```bash
# 1. Clone the repository
git clone https://github.com/Yash-0620/aegis-control-plane.git
cd aegis-control-plane

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set Environment Variables
export DATABASE_URL="postgresql://user:pass@host:5432/db"
export AEGIS_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"

# 4. Boot the Uvicorn Server
uvicorn issuer_node:app --host 0.0.0.0 --port 8000
```

Navigate to the `aegis-aip-sdk/` folder in this repository to view the SDK documentation and the 5-minute quickstart guide.

## 🔒 Why This Matters (For CISOs)
* **Model-Agnostic:** Works entirely at the network layer. Secures OpenAI, Anthropic, Meta, or custom models without touching their internal logic.
* **Least Privilege Enforcement:** Agents only get the exact cryptographic scopes they need for the exact tools they are allowed to use.
* **Audit-Ready:** Every single LLM action is cryptographically signed and logged, creating an immutable lineage for SOC2 and NYDFS compliance.
