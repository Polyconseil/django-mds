import datetime

import oauthlib.oauth2
import oauthlib.oauth2.rfc6749.tokens
import oauth2_provider.models
import oauth2_provider.oauth2_validators
from oauth2_provider.scopes import BaseScopes
from oauth2_provider.settings import oauth2_settings


from . import generators


def signed_token_generator(request):
    token_duration = datetime.timedelta(
        seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS
    )
    user = getattr(request, "user", None)
    token, payload = generators.generate_jwt_with_payload(
        request.client, token_duration=token_duration, user=user
    )
    # set claims on the request
    request.claims = payload
    return token


class Server(oauthlib.oauth2.Server):
    """Just swap the default token generator to signed_tokens."""

    def __init__(self, *args, **kwargs):
        if not kwargs.get("token_generator"):
            kwargs["token_generator"] = signed_token_generator
            kwargs[
                "refresh_token_generator"
            ] = oauthlib.oauth2.rfc6749.tokens.random_token_generator
        super().__init__(*args, **kwargs)


class OAuth2Validator(oauth2_provider.oauth2_validators.OAuth2Validator):
    def _create_access_token(self, expires, request, token, source_refresh_token=None):
        """Saves the token jti in the database."""
        access_token = oauth2_provider.models.get_access_token_model()(
            user=request.user,
            scope=token["scope"],
            expires=expires,
            token=token["access_token"],
            application=request.client,
            source_refresh_token=source_refresh_token,
            jti=request.claims["jti"],
        )
        access_token.save()
        return access_token


class AppScopes(BaseScopes):
    def get_all_scopes(self):
        Application = oauth2_provider.models.get_application_model()
        return {
            k: k
            for k in set(
                s
                for scopes in Application.objects.values_list("scopes", flat=True)
                for s in scopes
            )
        }

    def get_available_scopes(self, application=None, request=None, *args, **kwargs):
        return application.scopes

    def get_default_scopes(self, application=None, request=None, *args, **kwargs):
        return self.get_available_scopes(application, request, *args, **kwargs)
