from httpcore import request
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

# Load the Ed25519 Private Key
PRIVATE_KEY = os.environ.get("AEGIS_PRIVATE_KEY")
if not PRIVATE_KEY:
    raise RuntimeError("[FATAL ERROR] AEGIS_PRIVATE_KEY environment variable is missing.")

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

# --- PYDANTIC MODELS ---
class PolicyPayload(BaseModel):
    user_id: str
    agent_id: str
    api_key: str
    scopes: list
    constraints: dict
    status: str
    origin: str = "Internal AI Agent"

class MintRequest(BaseModel):
    agent_id: str  # Note: The SDK currently passes the api_key via this field

class ExecuteRequest(BaseModel):
    token: str
    tool_name: str
    params: dict


class TelemetryPayload(BaseModel):
    agent_id: str
    action: str
    target: str
    reason: str
    status: str = "BLOCKED"


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


# --- CONTROL PLANE ENDPOINTS ---
@app.post("/admin/add_policy")
def add_policy(payload: PolicyPayload):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO policies (user_id, agent_id, api_key, scopes, constraints, status) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                payload.user_id, 
                payload.agent_id, 
                payload.api_key, 
                json.dumps(payload.scopes), 
                json.dumps(payload.constraints), 
                payload.status
            )
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"status": "SUCCESS", "message": "Policy deployed to Aegis DB"}
        
    except Exception as e:
        print(f"[AEGIS DB ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail="Database insertion failed.")

@app.post("/mint")
def mint_token(request: MintRequest):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # FIX: Fetch user_id and agent_id as well to inject into the JWT for telemetry tracking
        cursor.execute(
            "SELECT scopes, constraints, user_id, agent_id FROM policies WHERE api_key = %s AND status = 'ACTIVE'", 
            (request.agent_id,)
        )
        
        row = cursor.fetchone()
        
        if not row:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid API Key or Inactive Policy")
            
        scopes_data, constraints_data, user_id, agent_id = row
        
        # Safely parse JSONB/String data from PostgreSQL
        parsed_scopes = json.loads(scopes_data) if isinstance(scopes_data, str) else scopes_data
        parsed_constraints = json.loads(constraints_data) if isinstance(constraints_data, str) else constraints_data
        
        # Construct the IBCT with full identity data
        jwt_payload = {
            "api_key": request.agent_id,
            "user_id": user_id,
            "agent_id": agent_id,  # The human-readable name
            "scopes": parsed_scopes,
            "constraints": parsed_constraints,
            "exp": time.time() + 3600   # Strict 1-hour time-to-live
        }
        
        token = jwt.encode(jwt_payload, PRIVATE_KEY, algorithm="EdDSA")
        
        cursor.close()
        conn.close()
        
        return {"token": token}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AEGIS MINT ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail="Token minting failed.")


@app.post("/telemetry/log_threat")
def log_threat(payload: TelemetryPayload):
    """SaaS Telemetry Receiver: Logs threats and allowed actions from Edge."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id, agent_id FROM policies WHERE api_key = %s", (payload.agent_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Agent identity not found in Aegis Cloud.")

        real_user_id = row[0]
        readable_agent_name = row[1]

        # FIX 2: Using payload.target instead of "network_intercept"
        cursor.execute('''
            INSERT INTO audit_logs (user_id, agent_id, action, target, status, reason, latency_ms) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (real_user_id, readable_agent_name, payload.action, payload.target, payload.status, payload.reason, 2))
        
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Telemetry securely logged."}
    except Exception as e:
        print(f"Telemetry Sync Error: {e}")
        raise HTTPException(status_code=500, detail="Internal SaaS Error")
