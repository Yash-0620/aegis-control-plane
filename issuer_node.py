from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import jwt
import crypto_core
import time
import sqlite3
import json

app = FastAPI(title="Aegis Enterprise Control Plane & Proxy")
master_priv, master_pub = crypto_core.setup_keys()

# --- THE BRAIN: Database Setup ---
def setup_database():
    # This creates a local database file called aegis_policies.db
    conn = sqlite3.connect("aegis_policies.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Create the Policy Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS policies
                      (agent_id TEXT PRIMARY KEY, scopes TEXT, constraints TEXT)''')
    
    # Seed the database with our CRO's official rules!
    # Notice: The rules live HERE on the server, not in the agent's code.
    # We are setting the max refund limit to $500 centrally.
    cursor.execute('''INSERT OR REPLACE INTO policies (agent_id, scopes, constraints)
                      VALUES (?, ?, ?)''', 
                   ("RefundBot-001", 
                    json.dumps(["stripe:refund:write"]), 
                    json.dumps({"max_refund_amount": 500}))) 
    conn.commit()
    return conn

# Boot up the database when the server starts
db_conn = setup_database()

def generate_constrained_ibct(private_key, agent_id, scopes, constraints):
    payload = {
        "agent_id": agent_id,
        "scopes": scopes,
        "constraints": constraints,
        "iat": int(time.time()),
        "exp": int(time.time()) + 300 
    }
    return jwt.encode(payload, private_key, algorithm="EdDSA")

# --- NODE 1: THE SMART ISSUER ---
class AgentRequest(BaseModel):
    agent_id: str
    # NOTICE: We deleted 'scopes' and 'constraints' from the request.
    # The agent is no longer allowed to ask for specific permissions!

@app.post("/mint")
def mint_token(req: AgentRequest):
    cursor = db_conn.cursor()
    
    # 1. Look up the agent in our secure database
    cursor.execute("SELECT scopes, constraints FROM policies WHERE agent_id=?", (req.agent_id,))
    row = cursor.fetchone()
    
    if not row:
        print(f"[SECURITY ALERT] Unknown agent attempted connection: {req.agent_id}")
        raise HTTPException(status_code=403, detail="Agent Identity not found in Aegis Database.")
        
    # 2. Extract the CRO's official rules
    db_scopes = json.loads(row[0])
    db_constraints = json.loads(row[1])
    
    print(f"--> [AEGIS DB] Found {req.agent_id}. Injecting scopes {db_scopes} and limits {db_constraints}.")
    
    # 3. Mint the badge using the DATABASE rules, entirely ignoring what the agent might want
    token = generate_constrained_ibct(master_priv, req.agent_id, db_scopes, db_constraints)
    return {"status": "secured", "ibct_envelope": token}

# --- NODE 3: THE SECURE PROXY ---
class ToolRequest(BaseModel):
    envelope: str
    tool_name: str
    action_params: dict

@app.post("/execute")
def proxy_request(req: ToolRequest):
    try:
        decoded_payload = jwt.decode(req.envelope, master_pub, algorithms=["EdDSA"])
        agent_id = decoded_payload["agent_id"]
        
        # 1. Scope Check
        required_scope = req.tool_name  # In a real system, you'd map tool_name to required scopes
        if required_scope not in decoded_payload["scopes"]:
            return {"status": "ACCESS_DENIED", "reason": f"Agent lacks scope: {required_scope}"}
            
        # 2. Constraint Check
        constraints = decoded_payload.get("constraints", {})
        if "max_refund_amount" in constraints:
            requested_amount = req.action_params.get("amount", 0)
            if requested_amount > constraints["max_refund_amount"]:
                return {"status": "ACCESS_DENIED", "reason": f"Blocked: ${requested_amount} exceeds central DB limit of ${constraints['max_refund_amount']}"}

        return {"status": "SUCCESS", "data": f"Executed {req.tool_name} with params {req.action_params}"}
        
    except jwt.ExpiredSignatureError:
        return {"status": "ACCESS_DENIED", "reason": "Token expired."}
    except jwt.InvalidTokenError:
        return {"status": "ACCESS_DENIED", "reason": "Intrusion detected."}
    

# --- NODE 4: THE ADMIN API (The "Dashboard" Backend) ---
class PolicyUpdate(BaseModel):
    agent_id: str
    scopes: list[str]
    constraints: dict

@app.post("/admin/add_policy")
def add_policy(req: PolicyUpdate):
    # This simulates the CRO clicking 'Save' on a dashboard
    cursor = db_conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO policies (agent_id, scopes, constraints)
                      VALUES (?, ?, ?)''', 
                   (req.agent_id, json.dumps(req.scopes), json.dumps(req.constraints)))
    db_conn.commit()
    return {"status": "policy_updated", "agent": req.agent_id}