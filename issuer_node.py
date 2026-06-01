from pydantic import BaseModel
from typing import List, Dict, Any

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
import secrets

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

# --- The Agnostic Payload Model ---
class PolicyPayload(BaseModel):
    agent_id: str  # Human-readable name (e.g., "HR-Agent-01")
    scopes: List[str]  # e.g., ["github:repo:delete", "stripe:refund:write"]
    # THE UPGRADE: 'constraints' no longer holds hardcoded rules like 'max_amount'.
    # It now strictly expects a valid JSON-Schema dictionary mapping to the scopes.
    constraints: Dict[str, Any] # e.g., {"stripe:refund:write": {"type": "object", "properties": {"amount": {"type": "number", "maximum": 100}}}}

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


# --- Control Plane - The Universal Policy Endpoint ---
@app.post("/admin/add_policy")
def add_policy(payload: PolicyPayload):
    try:
        # 1. Generate the standard secure API Identity Key
        api_key_hex = secrets.token_hex(16)
        api_key = f"aegis_live_{api_key_hex}"
        
        # 2. Convert standard lists and dynamic JSON-Schemas into JSON strings for Postgres
        scopes_json = json.dumps(payload.scopes)
        constraints_json = json.dumps(payload.constraints)
        
        # 3. Store the Universal Schema in Supabase
        cursor.execute(
            """
            INSERT INTO policies (agent_id, api_key, scopes, constraints, status)
            VALUES (%s, %s, %s, %s, 'ACTIVE')
            """,
            (payload.agent_id, api_key, scopes_json, constraints_json)
        )
        conn.commit()
        
        return {"status": "SUCCESS", "api_key": api_key, "agent_id": payload.agent_id}
    except Exception as e:
        conn.rollback()
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Database failure during schema injection")

# --- The Schema-Embedded Minting Endpoint ---
@app.post("/mint")
def mint_token(req: dict):
    api_key = req.get("api_key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API Key")

    try:
        # 1. Look up the Agent Identity by their API Key
        cursor.execute(
            """
            SELECT id, agent_id, scopes, constraints 
            FROM policies 
            WHERE api_key = %s AND status = 'ACTIVE'
            """, 
            (api_key,)
        )
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=403, detail="Invalid or revoked API Key")
            
        db_id, agent_name, scopes, constraints = row

        # Handle Postgres returning either strings or dicts natively
        scopes_data = json.loads(scopes) if isinstance(scopes, str) else scopes
        constraints_data = json.loads(constraints) if isinstance(constraints, str) else constraints

        # 2. Construct the Asymmetric Token Payload
        # We are bundling the exact JSON-Schema rules straight into the Ed25519 token
        payload = {
            "user_id": db_id,
            "agent_id": agent_name,
            "allowed_scopes": scopes_data,
            "schema_bounds": constraints_data # The Sidecar will read this schema locally
        }

        # 3. Sign the token mathematically using our Cloud Private Key
        token = jwt.encode(payload, AEGIS_PRIVATE_KEY, algorithm="EdDSA")
        return {"token": token}
        
    except Exception as e:
        print(f"Minting Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to mint Ed25519 token")


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
