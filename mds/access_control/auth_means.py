"""
Classes representing authentication means.

For now only JWT based authentication is supported as required by MDS specification:
https://github.com/CityOfLosAngeles/mobility-data-specification/tree/dev/agency#authorization

When using JWT as access tokens, the common usage is to not check with the
authorization server if the JWT is revoked and use short-lived tokens instead.
Because we fear most tokens in real world use of MDS will be long-lived  (contrary
to the spirit of JWT tokens), we optionally accept an introspection endpoint that will
be called to check token validity in cas it has been revoked

We could potentially handle access tokens that are not JWT.
In this case, the introspect_url would be required to retrieve the user scopes
"""
from typing import Optional


class BaseAuthMean:
    introspect_url: Optional[str]


class SecretKeyJwtBaseAuthMean(BaseAuthMean):
    secret_key: str

    def __init__(self, secret_key: str, introspect_url: str = None):
        self.secret_key = secret_key
        self.introspect_url = introspect_url


class PublicKeyJwtBaseAuthMean(BaseAuthMean):
    public_key: str

    def __init__(self, public_key: str, introspect_url: str = None):
        self.public_key = public_key
        self.introspect_url = introspect_url
