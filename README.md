# 🛡️ Aegis Protocol: Enterprise Control Plane

Welcome to the core infrastructure of the Agentic Identity Protocol (AIP). 

Aegis is the open-source standard for zero-trust AI agent security. It prevents autonomous AI agents (powered by LLMs like GPT-4, Claude, or Llama) from executing destructive actions (hallucinations, lateral escalation) when interacting with real-world enterprise infrastructure via the Model Context Protocol (MCP).

## 🏗️ The Architecture

This repository contains the **Aegis Control Plane** and **Secure Proxy**, which acts as the digital bouncer for your MCP servers.

1. **The Identity Issuer:** Mints dynamic, 5-minute Invocation-Bound Capability Tokens (IBCT) for AI agents using Ed25519 elliptic curve cryptography.
2. **The Secure Proxy:** A reverse proxy that intercepts all agent tool calls, mathematically verifies their blast radius against central database limits, and drops hallucinated requests before they ever touch your database or APIs.

## 🚀 Developers: Get the SDK

If you are an AI developer looking to secure your agents and stop hardcoding API keys, you don't need to run this control plane yourself. You just need our pip package.

**Install the Python SDK:**
```bash
pip install aegis-aip
```

Navigate to the `aegis-aip-sdk/` folder in this repository to view the SDK documentation and the 5-minute quickstart guide.

## 🔒 Why This Matters (For CISOs)
* **Model-Agnostic:** Works entirely at the network layer. Secures OpenAI, Anthropic, Meta, or custom models without touching their internal logic.
* **Least Privilege Enforcement:** Agents only get the exact cryptographic scopes they need for the exact tools they are allowed to use.
* **Audit-Ready:** Every single LLM action is cryptographically signed and logged, creating an immutable lineage for SOC2 and NYDFS compliance.