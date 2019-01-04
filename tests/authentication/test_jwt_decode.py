import jwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from mds.access_control.auth_means import (
    SecretKeyJwtBaseAuthMean,
    PublicKeyJwtBaseAuthMean,
)
from mds.access_control.jwt_decode import jwt_multi_decode


def test_jwt_multi_decode_fails_if_no_key_given():
    with pytest.raises(AssertionError):
        jwt_multi_decode([], "")


def test_jwt_multi_decode_secret_key():
    encoded_jwt = jwt.encode({"jti": "123"}, "MY-SECRET")
    decoded_jwt, introspect_url = jwt_multi_decode(
        [SecretKeyJwtBaseAuthMean("MY-SECRET")], encoded_jwt
    )
    assert decoded_jwt["jti"] == "123"


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


def test_jwt_multi_decode_public_key():
    (public_key, private_key) = gen_keys()

    encoded_jwt = jwt.encode({"jti": "123"}, private_key, algorithm="RS256")
    decoded_jwt, introspect_url = jwt_multi_decode(
        [PublicKeyJwtBaseAuthMean(public_key)], encoded_jwt
    )
    assert decoded_jwt["jti"] == "123"


def test_jwt_multiple_keys():
    (public_key_1, private_key_1) = gen_keys()
    (public_key_2, private_key_2) = gen_keys()

    encoded_jwt = jwt.encode({"jti": "123"}, private_key_2, algorithm="RS256")
    decoded_jwt, introspect_url = jwt_multi_decode(
        [
            PublicKeyJwtBaseAuthMean(public_key_1),
            PublicKeyJwtBaseAuthMean(public_key_2),
            SecretKeyJwtBaseAuthMean("MY-USELESS-SECRET"),
        ],
        encoded_jwt,
    )
    assert decoded_jwt["jti"] == "123"
