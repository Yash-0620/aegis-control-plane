import requests
import json

class AegisClient:
    def __init__(self, agent_id: str, control_plane_url: str):
        self.agent_id = agent_id
        self.control_plane_url = control_plane_url.rstrip('/')
        self.envelope = None

    def authenticate(self):
        """Fetches the dynamic IBCT badge from the Control Plane."""
        url = f"{self.control_plane_url}/mint"
        response = requests.post(url, json={"agent_id": self.agent_id})
        
        if response.status_code != 200:
            raise Exception(f"Aegis Auth Failed: {response.text}")
            
        self.envelope = response.json().get("ibct_envelope")
        print(f"[Aegis] Successfully authenticated agent: {self.agent_id}")
        return self.envelope

    def secure_tool_call(self, tool_name: str, action_params: dict):
        """Wraps an MCP tool call in the cryptographic envelope and routes it to the Proxy."""
        if not self.envelope:
            self.authenticate()

        url = f"{self.control_plane_url}/execute"
        secure_request = {
            "envelope": self.envelope,
            "tool_name": tool_name,
            "action_params": action_params
        }
        
        response = requests.post(url, json=secure_request)
        return response.json()