from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Generate the Ed25519 Asymmetric Keypair
private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Serialize to PEM format
priv_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

pub_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

print("=== PRIVATE KEY (SAVE TO RENDER ENV AS 'AEGIS_PRIVATE_KEY') ===")
print(priv_pem)
print("\n=== PUBLIC KEY (EMBED IN SIDECAR PROXY) ===")
print(pub_pem)