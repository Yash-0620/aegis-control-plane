# Aegis AIP (Agentic Identity Protocol) SDK 🛡️

**The Zero-Trust Enforcement SDK for Agentic AI.**

Aegis provides cryptographic, mathematical boundaries for LLM tool execution. It ensures that AI agents (Claude, GPT-4, Llama-3) cannot exfiltrate data, hallucinate unauthorized financial transactions, or execute destructive commands, even if their prompts are injected or jailbroken.

### The Problem
Relying on an LLM's internal safety alignment (RLHF) or prompt engineering is a massive compliance liability. If a hacker jailbreaks your customer support agent, the LLM will happily execute `refund(amount=50000)` or drop a production database. 

### The Solution: Universal Schema Verification at the Edge
Aegis sits at the **Network/Proxy layer**, completely agnostic to the underlying LLM and the target tool.
1. The Enterprise CISO configures strict mathematical boundaries (JSON-Schema, Regex, Integer limits) via the [Aegis Cloud Console](https://aegis-cloud-console.vercel.app/).
2. The agent is issued a stateless, Ed25519 cryptographically signed JWT containing that specific schema.
3. The SDK automatically intercepts your agent's tool calls and injects the `X-Aegis-IBCT` signature header.
4. Traffic is routed through your local [Aegis MCP Sidecar](https://github.com/Yash-0620/aegis-mcp-sidecar.git), which extracts the schema from the token and mathematically verifies the payload offline in `<2ms`. Unauthorized actions are dropped before they ever reach the tool.

### 🚀 5-Minute Quickstart

#### 1. Generate Your Cryptographic Schema
Head over to the [Aegis Cloud Console](https://aegis-cloud-console.vercel.app/) and provision a new Zero-Trust Policy. Define your exact JSON-Schema parameters (e.g., regex matching `*-dev-repo`) and copy the generated `API_KEY`.

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
    sidecar_url="http://localhost:8080/mcp/v1/tools/call" # Your local Aegis MCP Sidecar
)

# 2. Intercept and Proxy the Tool Call
llm_hallucinated_payload = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "github:repo:delete",
        "arguments": {"Github": "core-production-repo"} # Hacker attempts to delete prod
    }
}

# 3. Aegis intercepts, signs, and fires it at the Sidecar.
# The Sidecar executes the regex math and drops the payload offline in <2ms.
response = aegis.proxy_mcp_request(llm_hallucinated_payload)
print(response.json())
```

### Supported Enterprise Boundaries: The Universal Schema
Unlike legacy wrappers that require hardcoded Python logic for every new tool, Aegis enforces a Universal JSON-Schema Policy Engine. The sidecar is 100% tool-agnostic.

You can bind any mathematical constraint to your AI agent directly from the Cloud Console:

*   **String Regex**: Prevent unauthorized parameters (e.g., forcing all AWS bucket names to match ^.*-temp-.*$).
*   **Integer Bounds**: Block financial transactions exceeding a strict threshold (e.g., maximum: 500).
*   **Fail-Closed Strictness**: Aegis enforces additionalProperties: false by default, meaning any hallucinated parameter not explicitly defined in the CISO's schema will trigger an immediate HTTP 422 Unprocessable Entity containment breach.

### Architecture (V2.0 - Ed25519 Asymmetric Upgrade)
Aegis is built for high-throughput, Zero-Trust enterprise environments:
*   **Zero-Latency Edge:** The [Aegis MCP Sidecar](https://github.com/Yash-0620/aegis-mcp-sidecar.git) runs locally in your Docker network. It uses public-key cryptography to verify intents without making external cloud API calls.
*   **Stateless Scaling:** Tokens are fully self-contained. No database lookups are required at the execution edge.
*   **Cloud SIEM Integration:** Blocked threats (like schema breaches) and allowed traffic are asynchronously logged to the [Aegis Cloud Console](https://aegis-cloud-console.vercel.app/) for CISO forensics without slowing down the LLM pipeline.
