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
DATABASE_URL = os.environ.get("DATABASE_URL")

# Fail-fast safeguard: Prevent the server from booting if the DB URL is missing
if not DATABASE_URL:
    raise RuntimeError("[FATAL ERROR] DATABASE_URL environment variable is not set. Halting boot.")

# We will lock this down in a future sprint, but it's okay for local testing right now.
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
    status: str = None

class MintRequest(BaseModel):
    agent_id: str

class ExecuteRequest(BaseModel):
    token: str
    tool_name: str
    params: dict


class TelemetryPayload(BaseModel):
    agent_id: str  # This is the long API key sent by the Sidecar
    action: str
    reason: str


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
        
        # UPDATED: Inserting the status column
        cursor.execute('''
            INSERT INTO policies (agent_id, user_id, scopes, constraints, status) 
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (agent_id) DO UPDATE 
            SET user_id = EXCLUDED.user_id, scopes = EXCLUDED.scopes, constraints = EXCLUDED.constraints, status = EXCLUDED.status
        ''', (payload.agent_id, payload.user_id, str(payload.scopes), str(payload.constraints), payload.status))
        
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
    
    # UPDATED: Search using 'status' (which holds the token), and fetch the real 'agent_id' (row[3])
    cursor.execute("SELECT scopes, constraints, user_id, agent_id FROM policies WHERE status = %s", (req.agent_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Agent identity not found in Aegis Cloud.")

    parsed_scopes = safe_parse(row[0], [])
    parsed_constraints = safe_parse(row[1], {})

    jwt_payload = {
        "agent_id": row[3], # The clean human-readable name (e.g., "FinanceBot")
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
            
            # THE DEBUG BLOCK
            print(f"DEBUG: Complete Constraints Object Received: {constraints}", flush=True)
            print(f"DEBUG: Tool Name Requested: {req.tool_name}", flush=True)
            
            tool_constraints = constraints.get(req.tool_name, {})
            print(f"DEBUG: Tool Constraints Parsed: {tool_constraints}", flush=True)
            # --------------------------------
            
            internal_only = tool_constraints.get("internal_domains_only", True)
            
            if internal_only:
                allowed_domains = tool_constraints.get("allowed_domains", ["company.com"])
                print(f"DEBUG: Final Whitelist in use: {allowed_domains}", flush=True)
                
                if not any(target.endswith(f"@{domain}") for domain in allowed_domains):
                    status = "BLOCKED"
                    reason = f"Exfiltration Attempt - Domain {target.split('@')[-1]} not in whitelist"

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


@app.post("/telemetry/log_threat")
def log_threat(payload: TelemetryPayload):
    """SaaS Telemetry Receiver: Logs threats from external Enterprise Sidecars."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Reverse-Lookup the real user_id and human-readable agent name
        # Remember: the API key is stored in the 'status' column in your schema
        cursor.execute("SELECT user_id, agent_id FROM policies WHERE status = %s", (payload.agent_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Agent identity not found in Aegis Cloud.")

        real_user_id = row[0]
        readable_agent_name = row[1]

        # 2. Securely Insert into the SIEM Ledger
        cursor.execute('''
            INSERT INTO audit_logs (user_id, agent_id, action, target, status, reason, latency_ms) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (real_user_id, readable_agent_name, payload.action, "network_intercept", "BLOCKED", payload.reason, 12))
        
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Telemetry securely logged."}
    except Exception as e:
        print(f"Telemetry Sync Error: {e}")
        raise HTTPException(status_code=500, detail="Internal SaaS Error")