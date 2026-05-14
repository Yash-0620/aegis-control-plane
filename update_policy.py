import requests

# REPLACE WITH YOUR RENDER URL
RENDER_URL = "https://aegis-live-node.onrender.com"

new_policy = {
    "agent_id": "FileSystemBot",
    "scopes": ["fs:search:read"], # Notice: NO 'delete' scope
    "constraints": {}
}

res = requests.post(f"{RENDER_URL}/admin/add_policy", json=new_policy)
print(f"Policy Update Status: {res.json()}")