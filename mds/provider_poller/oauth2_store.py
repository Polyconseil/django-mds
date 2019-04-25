import json
import logging
import threading
import urllib.parse

from django.core.cache import caches

from cryptography import fernet
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from retrying import retry

from .settings import POLLER_TOKEN_CACHE, POLLER_TOKEN_ENCRYPTION_KEY


CACHE_KEY_PATTERN = "mds:oauth2-token:%s"  # Provider ID added

cache = caches[POLLER_TOKEN_CACHE]

logger = logging.getLogger(__name__)


def _encrypt_token(token):
    encoded = json.dumps(token).encode("utf8")  # Fernet needs bytes
    return fernet.Fernet(POLLER_TOKEN_ENCRYPTION_KEY).encrypt(encoded)


def _decrypt_token(encrypted):
    try:
        encoded = fernet.Fernet(POLLER_TOKEN_ENCRYPTION_KEY).decrypt(encrypted)
    except (fernet.InvalidToken, TypeError):  # The encryption key, not our token!
        return None
    else:
        return json.loads(encoded)


class OAuth2Store(threading.local):
    def __init__(self, provider):
        self.provider = provider

    def get_client(self):
        """Authenticate using the Backend Application Flow from OAuth2."""
        client_id = self.provider.api_authentication["client_id"]
        token = self._get_access_token()
        client = OAuth2Session(client_id, token=token)
        return client

    def _get_access_token(self):
        """Fetch and cache the token."""
        key = CACHE_KEY_PATTERN % self.provider.pk
        token = _decrypt_token(cache.get(key))
        if token:
            logger.debug("Token already in cache")
            return token
        token = self._fetch_access_token()
        cache.set(key, _encrypt_token(token), timeout=token["expires_in"] - 10)
        logger.debug("Token stored in cache")
        return token

    @retry(stop_max_attempt_number=2)
    def _fetch_access_token(self):
        """Fetch a new access token from the provider"""
        client_id = self.provider.api_authentication["client_id"]
        client_secret = self.provider.api_authentication["client_secret"]
        client = BackendApplicationClient(client_id=client_id)
        session = OAuth2Session(client=client)

        # The URL to fetch the token maybe on another base URL
        token_url = self.provider.oauth2_url
        if not token_url:
            token_url = urllib.parse.urljoin(
                self.provider.base_api_url, "/oauth2/token"
            )
            if self.provider.api_configuration.get("trailing_slash"):
                token_url += "/"

        # Provider-specific parameters to request the token
        kwargs = {}
        try:
            kwargs.update(self.provider.api_configuration["token_params"])
        except KeyError:
            pass

        token = session.fetch_token(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            **kwargs
        )
        return token

    def flush_token(self):
        key = CACHE_KEY_PATTERN % self.provider.pk
        logger.debug("Token deleted from cache")
        cache.delete(key)
