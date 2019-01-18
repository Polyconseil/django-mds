import jwt
import pytest

from mds.access_control.auth_means import (
    SecretKeyJwtBaseAuthMean,
    PublicKeyJwtBaseAuthMean,
)
from mds.access_control.jwt_decode import jwt_multi_decode
from tests.auth_helpers import gen_keys


def test_jwt_multi_decode_fails_if_no_key_given():
    with pytest.raises(AssertionError):
        jwt_multi_decode([], "")


def test_jwt_multi_decode_secret_key():
    encoded_jwt = jwt.encode({"jti": "123"}, "MY-SECRET")
    decoded_jwt, introspect_url = jwt_multi_decode(
        [SecretKeyJwtBaseAuthMean("MY-SECRET")], encoded_jwt
    )
    assert decoded_jwt["jti"] == "123"


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
