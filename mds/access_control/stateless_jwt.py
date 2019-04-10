from django.conf import settings
from django.utils.encoding import smart_text
from rest_framework.authentication import BaseAuthentication, get_authorization_header

from .authenticate import authenticate


class StatelessJwtAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        encoded_jwt = self.extract_token(request)
        if encoded_jwt is None:
            return None

        if not settings.AUTH_MEANS:
            raise Exception(
                "JWT authentication configuration is incomplete: "
                + "neither secret nor public key found"
            )

        user = authenticate(settings.AUTH_MEANS, encoded_jwt)

        return user, None

    @staticmethod
    def extract_token(request):
        auth_header = get_authorization_header(request)

        if not auth_header:
            # only check on GET method
            # for other methods such as POST, you would usually specify the header and the token in it
            return request.GET.get("token", None)

        auth_header_prefix = "Bearer ".lower()
        auth = smart_text(auth_header)

        if not auth.lower().startswith(auth_header_prefix):
            return None

        return auth[len(auth_header_prefix) :]
