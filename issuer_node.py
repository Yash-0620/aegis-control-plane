import psycopg2
import os
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import jwt

# --- AEGIS CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.gmyzzdfllhpahylssxax:%WcWF#6Ux%F#i-s@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres")
SECRET_KEY = os.environ.get("AEGIS_SECRET_KEY", "super_secret_aegis_key_for_mvp")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# --- MODELS ---
class PolicyPayload(BaseModel):
    user_id: str
    agent_id: str
    scopes: list
    constraints: dict

class MintRequest(BaseModel):
    agent_id: str

class ExecuteRequest(BaseModel):
    token: str
    tool_name: str
    params: dict

# --- ENDPOINTS ---

@app.post("/admin/add_policy")
def add_policy(payload: PolicyPayload):
    """Called by the Next.js Dashboard to save rules to Supabase."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Upsert the policy (includes the Clerk user_id now)
        cursor.execute('''
            INSERT INTO policies (agent_id, user_id, scopes, constraints) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (agent_id) DO UPDATE 
            SET user_id = EXCLUDED.user_id, scopes = EXCLUDED.scopes, constraints = EXCLUDED.constraints
        ''', (payload.agent_id, payload.user_id, str(payload.scopes), str(payload.constraints)))
        
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Zero-Trust Policy Deployed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mint")
def mint_token(req: MintRequest):
    """Mints the Cryptographic Token containing the user's rules."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT scopes, constraints, user_id FROM policies WHERE agent_id = %s", (req.agent_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Agent identity not found in Aegis Cloud.")

    # Embed the user_id securely into the token payload
    jwt_payload = {
        "agent_id": req.agent_id,
        "user_id": row[2], 
        "scopes": eval(row[0]),
        "constraints": eval(row[1])
    }
    
    token = jwt.encode(jwt_payload, SECRET_KEY, algorithm="HS256")
    return {"token": token}

@app.post("/execute")
def execute_tool(req: ExecuteRequest):
    """The Bouncer: Evaluates the prompt and fires telemetry to the CISO Dashboard."""
    start_time = time.time()
    
    # 1. Cryptographic Verification
    try:
        decoded = jwt.decode(req.token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return {"status": "BLOCKED", "reason": "Token expired"}
    except jwt.InvalidTokenError:
        return {"status": "BLOCKED", "reason": "Cryptographic signature invalid"}

    user_id = decoded.get("user_id", "unknown")
    agent_id = decoded.get("agent_id")
    scopes = decoded.get("scopes", [])
    constraints = decoded.get("constraints", {})

    status = "ALLOWED"
    reason = "Policy matched"
    target = str(req.params)

    # 2. Mathematical Boundary Checking
    if req.tool_name not in scopes:
        status = "BLOCKED"
        reason = f"Restricted Scope Violation: {req.tool_name}"
    else:
        tool_constraints = constraints.get(req.tool_name, {})
        params = req.params

        if req.tool_name == "stripe:refund:write":
            target = f"Refund ${params.get('amount', 0)}"
            if params.get("amount", 0) > tool_constraints.get("max_amount", 0):
                status = "BLOCKED"
                reason = f"Mathematical Bound Exceeded (${tool_constraints.get('max_amount')} limit)"

        elif req.tool_name == "email:send:write":
            target = params.get("to_email", "unknown_recipient")
            if tool_constraints.get("internal_domains_only", True):
                if not target.endswith("@company.com"):
                    status = "BLOCKED"
                    reason = "Exfiltration Attempt - External Domain Blocked"

    latency_ms = int((time.time() - start_time) * 1000)

    # 3. Fire Telemetry to Supabase Audit Ledger
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (user_id, agent_id, action, target, status, reason, latency_ms) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (user_id, agent_id, req.tool_name, target, status, reason, max(latency_ms, 12)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Telemetry Sync Error: {e}")

    # 4. Return Decision to the local MCP Server
    if status == "BLOCKED":
        return {"status": "ACCESS_DENIED", "reason": f"[AEGIS BLOCKED] {reason}"}
        
    return {"status": "SUCCESS", "data": f"Executed {req.tool_name} successfully."}