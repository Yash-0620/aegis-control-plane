import requests
import json

class AegisClient:
    def __init__(self, agent_id: str, control_plane_url: str):
        self.agent_id = agent_id
        self.control_plane_url = control_plane_url.rstrip('/')
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

    def secure_tool_call(self, tool_name: str, params: dict):
        """Wraps an MCP tool call in the cryptographic token and routes it to the Proxy."""
        url = f"{self.control_plane_url}/execute"
        secure_request = {
            "token": self.token,
            "tool_name": tool_name,
            "params": params
        }
        
        response = requests.post(url, json=secure_request)
        return response.json()