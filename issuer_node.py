import psycopg2
import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import jwt

# --- AEGIS CONFIGURATION ---
# Render will automatically inject your Supabase URL here
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:%25WcWF%236Ux%25F%23i-s@db.gmyzzdfllhpahylssxax.supabase.co:5432/postgres")
SECRET_KEY = os.environ.get("AEGIS_SECRET_KEY", "super_secret_aegis_key_for_mvp")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE SETUP ---
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS policies 
                          (agent_id TEXT PRIMARY KEY, scopes TEXT, constraints TEXT)''')
        conn.commit()
        conn.close()
        print("Aegis Database Initialized Successfully.")
    except Exception as e:
        print(f"Database Initialization Error: {e}")

init_db()

# --- DATA MODELS ---
class PolicyPayload(BaseModel):
    agent_id: str
    scopes: list[str]
    constraints: dict

class AgentAuth(BaseModel):
    agent_id: str

class ToolRequest(BaseModel):
    token: str
    tool_name: str
    params: dict

# --- CONTROL PLANE ENDPOINTS ---
@app.post("/admin/add_policy")
def add_policy(payload: PolicyPayload):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Postgres UPSERT logic
    cursor.execute("""
        INSERT INTO policies (agent_id, scopes, constraints) 
        VALUES (%s, %s, %s)
        ON CONFLICT (agent_id) 
        DO UPDATE SET scopes = EXCLUDED.scopes, constraints = EXCLUDED.constraints
    """, (payload.agent_id, json.dumps(payload.scopes), json.dumps(payload.constraints)))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Policy for {payload.agent_id} synced."}

@app.post("/mint")
def mint_badge(auth: AgentAuth):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT scopes, constraints FROM policies WHERE agent_id=%s", (auth.agent_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=403, detail="Agent not registered in Aegis Cloud.")

    scopes = json.loads(row[0])
    constraints = json.loads(row[1])

    payload = {
        "agent_id": auth.agent_id,
        "scopes": scopes,
        "constraints": constraints,
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return {"token": token}

# --- THE UNIVERSAL BOUNCER (PROXY) ---
@app.post("/execute")
def proxy_request(req: ToolRequest):
    try:
        # 1. Verify Cryptographic Envelope
        decoded = jwt.decode(req.token, SECRET_KEY, algorithms=["HS256"])
        agent_id = decoded.get("agent_id")
        scopes = decoded.get("scopes", [])
        constraints = decoded.get("constraints", {})

        # 2. Scope Validation
        if req.tool_name not in scopes:
            return {"status": "ACCESS_DENIED", "reason": f"Agent lacks scope: {req.tool_name}"}

        # 3. Contextual Parameter Bounding
        tool_constraints = constraints.get(req.tool_name, {})
        params = req.params

        if req.tool_name == "stripe:refund:write":
            if params.get("amount", 0) > tool_constraints.get("max_amount", 0):
                return {"status": "ACCESS_DENIED", "reason": f"Blocked: ${params.get('amount')} exceeds limit of ${tool_constraints.get('max_amount')}"}

        elif req.tool_name == "fs:search:read":
            file_type = params.get("file_extension")
            allowed_exts = tool_constraints.get("allowed_extensions", [])
            if file_type not in allowed_exts:
                return {"status": "ACCESS_DENIED", "reason": f"Blocked: File type '{file_type}' not in allowed extensions {allowed_exts}"}

        elif req.tool_name == "email:send:write":
            if tool_constraints.get("internal_domains_only", True):
                recipient = params.get("to_email", "")
                if not recipient.endswith("@company.com"):
                    return {"status": "ACCESS_DENIED", "reason": "Blocked: Agent restricted to internal corporate emails only."}

        return {"status": "SUCCESS", "data": f"Executed {req.tool_name} with params {params}"}

    except jwt.InvalidTokenError:
        return {"status": "ACCESS_DENIED", "reason": "Invalid or tampered cryptographic badge."}