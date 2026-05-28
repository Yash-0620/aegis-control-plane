import requests
import json

class AegisClient:
    def __init__(self, agent_id: str, control_plane_url: str, sidecar_url: str = "http://localhost:8080"):
        self.agent_id = agent_id
        self.control_plane_url = control_plane_url.rstrip('/')
        self.sidecar_url = sidecar_url.rstrip('/')
        
        # Authenticate and grab the token on initialization
        self.token = self.authenticate()

    def authenticate(self):
        """Fetches the dynamic cryptographic token from the Control Plane."""
        url = f"{self.control_plane_url}/mint"
        response = requests.post(url, json={"agent_id": self.agent_id})
        
        if response.status_code != 200:
            raise Exception(f"Aegis Auth Failed: {response.text}")
            
        token = response.json().get("token")
        print(f"[Aegis] Successfully authenticated agent: {self.agent_id}")
        return token

    def proxy_mcp_request(self, payload: dict, path: str = "/mcp"):
        """
        The Interceptor: Forwards any standard MCP request through the Sidecar,
        automatically injecting the cryptographic X-Aegis-IBCT header.
        """
        headers = {
            "Content-Type": "application/json",
            "X-Aegis-IBCT": self.token
        }
        
        try:
            # Route traffic through the local Sidecar instead of the Cloud
            response = requests.post(f"{self.sidecar_url}{path}", headers=headers, json=payload)
            
            # If the Sidecar blocks the request, it severs it with a 401/403
            if response.status_code in [401, 403]:
                return {
                    "status": "ACCESS_DENIED", 
                    "reason": response.json().get("detail", "Blocked by Aegis Sidecar")
                }
            
            # Try to return the JSON response from the target server
            try:
                return response.json()
            except ValueError:
                # Fallback if the target server returns raw text/html
                return {"status": "SUCCESS", "raw_response": response.text}
                
        except requests.exceptions.RequestException as e:
            return {"status": "ERROR", "reason": f"Sidecar Connection Failed: {str(e)}"}

    def secure_tool_call(self, tool_name: str, params: dict):
        """
        Helper method: Constructs a standard MCP tools/call JSON-RPC payload 
        and routes it securely through the proxy.
        """
        mcp_payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params
            }
        }
        return self.proxy_mcp_request(mcp_payload)