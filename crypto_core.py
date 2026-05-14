import jwt
import time
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def setup_keys():
    """Generates the master Ed25519 Private/Public keys for Aegis."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    # We are keeping them in memory for the MVP to stay fast and simple
    return private_key, public_key

def generate_ibct(private_key, agent_id, scopes):
    """Creates the Invocation-Bound Capability Token (IBCT)"""
    
    # This is the payload - the exact identity and rules for the AI robot
    payload = {
        "agent_id": agent_id,
        "scopes": scopes,
        "iat": int(time.time()), # Issued at (current time)
        "exp": int(time.time()) + 300 # Expires in 5 minutes (300 seconds)
    }
    
    # Sign the token using our master private key
    token = jwt.encode(payload, private_key, algorithm="EdDSA")
    return token

# --- LET'S TEST IT ---
if __name__ == "__main__":
    print("--- AEGIS TERMINAL ONLINE ---")
    print("Generating Master Keys...")
    master_priv, master_pub = setup_keys()
    
    print("\nMinting IBCT for 'RefundBot'...")
    # We are giving this agent permission to write refunds to stripe
    test_token = generate_ibct(master_priv, "RefundBot-001", ["stripe:refund:write"])
    
    print("\nSUCCESS. Here is the unforgeable cryptographic ID badge:")
    print(test_token)
    print("\n-----------------------------")