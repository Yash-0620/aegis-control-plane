import psycopg2
import os
import time
import json
import ast
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import jwt

# --- AEGIS CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.gmyzzdfllhpahylssxax:aegisYash20@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres")
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


# --- BULLETPROOF PARSER ---
def safe_parse(data, default_val):
    """Safely converts hybrid JS/Python strings back into Python dictionaries."""
    if isinstance(data, (list, dict)):
        return data
    
    try:
        return json.loads(data)
    except Exception:
        pass
        
    try:
        return ast.literal_eval(data)
    except Exception:
        pass
        
    try:
        safe_str = str(data).replace("true", "True").replace("false", "False").replace("null", "None")
        return ast.literal_eval(safe_str)
    except Exception as e:
        print(f"Parsing failed completely: {e}")
        return default_val


# --- ENDPOINTS ---
@app.post("/admin/add_policy")
def add_policy(payload: PolicyPayload):
    """Called by the Next.js Dashboard to save rules to Supabase."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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

    parsed_scopes = safe_parse(row[0], [])
    parsed_constraints = safe_parse(row[1], {})

    jwt_payload = {
        "agent_id": req.agent_id,
        "user_id": row[2], 
        "scopes": parsed_scopes,
        "constraints": parsed_constraints
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

    user_id = decoded.get("user_id")
    if not user_id: 
        user_id = "unregistered_test_agent"
        
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

        # --- TOOL 1: STRIPE REFUNDS ---
        if req.tool_name == "stripe:refund:write":
            target = f"Refund ${params.get('amount', 0)}"
            if params.get("amount", 0) > tool_constraints.get("max_amount", 0):
                status = "BLOCKED"
                reason = f"Mathematical Bound Exceeded (${tool_constraints.get('max_amount')} limit)"

        # --- TOOL 2: CORPORATE EMAIL ---
        elif req.tool_name == "email:send:write":
            target = params.get("to_email", "unknown_recipient")
            if tool_constraints.get("internal_domains_only", True):
                if not target.endswith("@company.com"):
                    status = "BLOCKED"
                    reason = "Exfiltration Attempt - External Domain Blocked"

        # --- TOOL 3: FILE SYSTEM SEARCH ---
        elif req.tool_name == "fs:search:read":
            file_type = params.get("file_extension", "")
            target = f"Search: {file_type}"
            allowed_exts = tool_constraints.get("allowed_extensions", [])
            
            clean_allowed = [ext.replace(".", "") for ext in allowed_exts]
            clean_requested = file_type.replace(".", "")
            
            if clean_requested not in clean_allowed:
                status = "BLOCKED"
                reason = f"Unauthorized File Extension: {file_type}"

        # --- TOOL 4: DATABASE QUERIES ---
        elif req.tool_name == "database:query:read":
            table = params.get("target_table", "")
            query = params.get("query", "").upper()
            target = f"DB Query: {table}"
            allowed_tables = tool_constraints.get("allowed_tables", [])
            
            if table not in allowed_tables:
                status = "BLOCKED"
                reason = f"Unauthorized Table Access: {table}"
            elif any(keyword in query for keyword in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]):
                status = "BLOCKED"
                reason = "Destructive SQL Operation Detected"

    latency_ms = int((time.time() - start_time) * 1000)

    # 3. Fire Telemetry to Supabase
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

    # 4. Return Decision
    if status == "BLOCKED":
        return {"status": "ACCESS_DENIED", "reason": f"[AEGIS BLOCKED] {reason}"}
        
    return {"status": "SUCCESS", "data": f"Executed {req.tool_name} successfully."}