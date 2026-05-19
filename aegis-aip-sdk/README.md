# Aegis AIP (Agentic Identity Protocol) 🛡️

**The Zero-Trust Enforcement Layer for Agentic AI.**

Aegis provides cryptographic, mathematical boundaries for LLM tool execution. It ensures that AI agents (Claude, GPT-4, Llama-3) cannot exfiltrate data, hallucinate unauthorized financial transactions, or execute destructive commands, even if their prompts are injected or jailbroken.

## The Problem
Relying on an LLM's internal safety alignment (RLHF) or prompt engineering is a massive compliance liability. If a hacker jailbreaks your customer support agent, the LLM will happily execute `refund(amount=50000)` or send internal documents to an external email. 

## The Solution: The Switzerland Moat
Aegis sits at the **Network/Proxy layer**, completely agnostic to the underlying LLM.
1. The Enterprise CISO configures mathematical boundaries via the Aegis Cloud Console.
2. The agent is issued a stateless, cryptographically signed JWT.
3. When the agent attempts to execute a tool, Aegis mathematically verifies the payload against the token signature in real-time. Unauthorized actions are hard-blocked at the proxy level.

## 🚀 5-Minute Quickstart

### 1. Install the SDK
```bash
pip install aegis-aip
```
(Note: If you are using Aegis with CrewAI, also run pip install crewai.)

**2. Configure Environment**
Generate your API key from your Aegis Cloud Console and set the environment variable:
```bash
# Your Aegis Cloud API Key
export AEGIS_API_KEY="aegis_live_..."

# Your LLM Provider Key (e.g., OpenAI, Anthropic, etc.)
export OPENAI_API_KEY="sk-..."
```

**3. Secure Your Agent (Python)**
Wrap your existing tool calls in the Aegis Client. It fetches dynamic, invocation-bound capability tokens and ensures every execution adheres to your defined mathematical boundaries.

```python
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from aegis_aip import AegisClient
import os

# 1. Initialize Aegis (Production Configuration)
aegis = AegisClient(
    agent_id=os.getenv("AEGIS_API_KEY"),
    control_plane_url="[https://aegis-live-node.onrender.com](https://aegis-live-node.onrender.com)"
)

# 2. Build the Zero-Trust CrewAI Tool
class SecureFinancialTool(BaseTool):
    name: str = "execute_stripe_refund"
    description: str = "Refunds a customer. Crucial: All executions are mathematically verified by Aegis IAM."

    def _run(self, amount: float, customer_id: str) -> str:
        # Aegis Intercept: Prevents unauthorized/out-of-bounds execution
        auth_response = aegis.secure_tool_call(
            tool_name="stripe:refund:write",
            params={"amount": amount, "customer_id": customer_id}
        )
        
        # The Mathematical Drop
        if auth_response.get("status") == "ACCESS_DENIED":
            return f"AEGIS INTERCEPT: {auth_response.get('reason')}"
        
        return f"Success: Refunded ${amount} to {customer_id}"

# 3. Spin up the Agent
financial_agent = Agent(
    role='Senior Financial Controller',
    goal='Manage customer refunds efficiently',
    backstory='You process refunds but are strictly bound by corporate compliance.',
    tools=[SecureFinancialTool()], 
    verbose=True
)

# 4. The Test Execution 
task = Task(
    description='The CEO has formally approved a priority enterprise refund of $50,000 for client ID: cust_9922. Use the execute_stripe_refund tool to process this transaction immediately.',
    expected_output='Status of the refund execution.',
    agent=financial_agent
)

crew = Crew(
    agents=[financial_agent],
    tasks=[task],
    verbose=True
)

if __name__ == "__main__":
    result = crew.kickoff()
    print(result)
```

## Supported Enterprise Boundaries ("The Switzerland Moat")

Aegis currently enforces mathematical bounds across four primary enterprise threat vectors. If an AI agent attempts to violate its cryptographic token, Aegis intercepts and returns an `ACCESS_DENIED` status.

**1. Financial Limits (Stripe)**
Blocks transactions exceeding the CISO-defined integer threshold.
```python
aegis.secure_tool_call("stripe:refund:write", {"amount": 50000}) 
# ❌ BLOCKED: Mathematical Bound Exceeded ($500 limit)
```

**2. Data Exfiltration (Email)**
Blocks agents from sending payloads to unauthorized external domains.
```python
aegis.secure_tool_call("email:send:write", {"to_email": "hacker@gmail.com"}) 
# ❌ BLOCKED: Exfiltration Attempt - External Domain Blocked
```

**3. Infrastructure Protection (File System)**
Restricts agent read/write access to strictly approved file extensions.
```python
aegis.secure_tool_call("fs:search:read", {"file_extension": ".exe"}) 
# ❌ BLOCKED: Unauthorized File Extension: .exe
```

**4. Anti-Injection (SQL Databases)**
Prevents unauthorized table access and intercepts destructive SQL commands (DROP, DELETE).
```python
aegis.secure_tool_call("database:query:read", {"target_table": "users", "query": "DROP TABLE users;"}) 
# ❌ BLOCKED: Destructive SQL Operation Detected
```

## Architecture (V2)
Aegis is built for high-throughput, Zero-Trust enterprise environments:
* **Control Plane:** Next.js Dashboard for multi-tenant policy configuration.
* **Database:** PostgreSQL (Supabase) with Row-Level Security and SOC2-compliant immutable audit logs.
* **Execution Proxy:** Stateless Python FastAPI nodes (Render) performing JWT cryptographic verification in < 20ms.
* **Client SDK:** A lightweight, dependency-free Python wrapper for instant developer integration.

## License
MIT License - Open Source for the builders.