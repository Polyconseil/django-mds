import datetime

from django.utils.translation import ugettext as _

from oauth2_provider.contrib.rest_framework import OAuth2Authentication, TokenHasScope

from rest_framework import exceptions
from rest_framework import permissions
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from mds.access_control.scopes import SCOPE_PROVIDER
from . import generators
from . import models


class LongLivedTokenView(GenericAPIView):
    """Implements an endpoint to generate long lived (JWT) tokens.

    This is an alternate authentication method to Oauth2.
    An authorized user can generate such tokens and then transmit
    it to the token owner for future use with our API.
    """

    authentication_classes = (OAuth2Authentication,)
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]
    required_scopes = [SCOPE_PROVIDER]

    class RequestSerializer(serializers.Serializer):
        app_owner = serializers.UUIDField(
            help_text="The owner for which the token is generated."
        )
        token_duration = serializers.IntegerField(
            help_text="Token duration in seconds."
        )

    class ResponseSerializer(serializers.Serializer):
        access_token = serializers.CharField()
        token_type = serializers.ChoiceField(choices=["bearer"])
        expires_in = serializers.IntegerField()

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm("authent.add_accesstoken"):
            raise exceptions.PermissionDenied()

        serializer = self.RequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        application = models.Application.objects.filter(
            owner=validated_data["app_owner"]
        ).last()
        if not application:
            raise exceptions.ValidationError(
                {
                    "app_owner": _("No application known for owner %s")
                    % validated_data["app_owner"]
                }
            )
        token_duration = datetime.timedelta(
            seconds=serializer.validated_data["token_duration"]
        )

        token = generators.generate_jwt(application, token_duration)
        serializer = self.ResponseSerializer(
            instance={
                "access_token": token,
                "token_type": "bearer",
                "expires_in": validated_data["token_duration"],
            }
        )
        return Response(serializer.data, status=200)
