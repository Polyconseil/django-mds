import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt


BASE_NUM_QUERIES = sum([1, 2])  # revoked tokens  # savepoints


def auth_header(*scopes, provider_id=None):
    claims = {
        "jti": "11111111-1111-1111-1111-111111111111",
        "sub": "test-user",
        "scope": " ".join(scopes),
    }

    if provider_id:
        claims["app_owner"] = str(provider_id)

    return {
        "HTTP_AUTHORIZATION": "Bearer "
        + jwt.encode(claims, os.environ["MDS_AUTH_SECRET_KEY"]).decode("utf-8")
    }


def gen_keys() -> (str, str):
    key = rsa.generate_private_key(
        public_exponent=65537, key_size=512, backend=default_backend()
    )
    private_key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return public_key_pem, private_key_pem
