# Aegis AIP (Agentic Identity Protocol) SDK 🛡️

**The Zero-Trust Enforcement SDK for Agentic AI.**

Aegis provides cryptographic, mathematical boundaries for LLM tool execution. It ensures that AI agents (Claude, GPT-4, Llama-3) cannot exfiltrate data, hallucinate unauthorized financial transactions, or execute destructive commands, even if their prompts are injected or jailbroken.

### The Problem
Relying on an LLM's internal safety alignment (RLHF) or prompt engineering is a massive compliance liability. If a hacker jailbreaks your customer support agent, the LLM will happily execute `refund(amount=50000)` or send internal documents to an external email.

### The Solution: Stateless Asymmetric Edge Verification
Aegis sits at the **Network/Proxy layer**, completely agnostic to the underlying LLM.
1. The Enterprise CISO configures mathematical boundaries via the [Aegis Cloud Console](https://aegis-cloud-console.vercel.app/).
2. The agent is issued a stateless, Ed25519 cryptographically signed JWT.
3. The SDK automatically intercepts your agent's tool calls and injects the `X-Aegis-IBCT` signature header.
4. Traffic is routed through your local [Aegis MCP Sidecar](https://github.com/Yash-0620/aegis-mcp-sidecar.git), which mathematically verifies the payload against the token signature offline in `<2ms`. Unauthorized actions are dropped before they ever reach the tool.

### 🚀 5-Minute Quickstart

#### 1. Generate Your Cryptographic Identity
Head over to the [Aegis Cloud Console](https://aegis-cloud-console.vercel.app/) and provision a new Zero-Trust Policy (e.g., maximum financial transaction limits or restricted database operations). Copy the generated `API_KEY`.

#### 2. Install the SDK
```bash
pip install aegis-aip
```

#### 3. Configure the Interceptor (Python)
Instead of exposing your tools directly to the LLM, use the Aegis Client to intercept and wrap the payload. It automatically fetches your Ed25519 token and routes the traffic through your local sidecar container.

```python
import os
from aegis_aip.client import AegisClient

# 1. Initialize the SDK
aegis = AegisClient(
    api_key=os.getenv("AEGIS_API_KEY"),
    control_plane_url="[https://aegis-live-node.onrender.com](https://aegis-live-node.onrender.com)",
    sidecar_url="http://localhost:8080" # Your local Aegis MCP Sidecar
)

# 2. Intercept and Proxy the Tool Call
llm_hallucinated_payload = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "stripe:refund:write",
        "arguments": {"amount": 50000} # Hacker attempts a $50k refund
    }
}

# 3. Aegis intercepts, signs, and fires it at the Sidecar.
# The Sidecar mathematically blocks it offline in <2ms.
response = aegis.proxy_mcp_request(llm_hallucinated_payload)
print(response.json())
```

### Supported Enterprise Boundaries
Aegis currently enforces mathematical bounds across four primary enterprise threat vectors. If an AI agent attempts to violate its cryptographic token, the Sidecar intercepts and returns an `HTTP 403 Forbidden` status.

*   **Financial Limits (Stripe)**: Blocks transactions exceeding the CISO-defined integer threshold.
*   **Data Exfiltration (Email)**: Blocks agents from sending payloads to unauthorized external domains.
*   **Infrastructure Protection (File System)**: Restricts agent read/write access to strictly approved file extensions.
*   **Anti-Injection (SQL Databases)**: Prevents unauthorized table access and intercepts destructive SQL commands (`DROP`, `DELETE`).

### Architecture (V1.0 - Ed25519 Asymmetric Upgrade)
Aegis is built for high-throughput, Zero-Trust enterprise environments:
*   **Zero-Latency Edge:** The [Aegis MCP Sidecar](https://github.com/Yash-0620/aegis-mcp-sidecar.git) runs locally in your Docker network. It uses public-key cryptography to verify intents without making external cloud API calls.
*   **Stateless Scaling:** Tokens are fully self-contained. No database lookups are required at the execution edge.
*   **Cloud SIEM Integration:** Blocked threats and allowed traffic are asynchronously logged to the [Aegis Cloud Console](https://aegis-cloud-console.vercel.app/) for CISO forensics without slowing down the LLM pipeline.
