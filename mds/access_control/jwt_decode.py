from typing import List, Dict

import jwt

from .auth_means import BaseAuthMean, PublicKeyJwtBaseAuthMean, SecretKeyJwtBaseAuthMean


def jwt_multi_decode(auth_means: List[BaseAuthMean], encoded_jwt: str) -> (Dict, str):
    """
    Try all available secret and public keys to decode the JWT
    """

    assert auth_means, "At least one JWT key must be provided"

    exception_holder = jwt.InvalidSignatureError()

    header = jwt.get_unverified_header(encoded_jwt)
    alg = header["alg"]

    for auth_mean in auth_means:
        if alg == "RS256" and isinstance(auth_mean, PublicKeyJwtBaseAuthMean):
            try:
                return (
                    jwt.decode(encoded_jwt, auth_mean.public_key, algorithms="RS256"),
                    auth_mean.introspect_url,
                )
            except jwt.InvalidSignatureError as e:
                exception_holder = e
        elif isinstance(auth_mean, SecretKeyJwtBaseAuthMean):
            try:
                return (
                    jwt.decode(encoded_jwt, auth_mean.secret_key, algorithms="HS256"),
                    auth_mean.introspect_url,
                )
            except jwt.InvalidSignatureError as e:
                exception_holder = e

    raise exception_holder
