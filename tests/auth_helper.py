import os

import jwt


def auth_header(*scopes, provider_id=None):
    claims = {"jti": "123", "sub": "test-user", "scope": " ".join(scopes)}

    if provider_id:
        claims["provider_id"] = provider_id

    return {
        "HTTP_AUTHORIZATION": "Bearer "
        + jwt.encode(claims, os.environ["MDS_AUTH_SECRET_KEY"]).decode("utf-8")
    }
