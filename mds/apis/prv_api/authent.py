from uuid import uuid4
from mds.authent import models

from django.utils.translation import ugettext as _

from oauth2_provider.contrib.rest_framework import OAuth2Authentication, TokenHasScope

from rest_framework import exceptions
from rest_framework import permissions
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from mds.apis import utils
from mds.access_control.scopes import SCOPE_PROVIDER

import mds.authent.public_api as public_api


class AppCreationView(GenericAPIView):
    """ Implements an endpoint to create Oauth2 application for providers
    """

    authentication_classes = (OAuth2Authentication,)
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]
    required_scopes = [SCOPE_PROVIDER]

    class CreationRequestSerializer(serializers.Serializer):
        app_name = serializers.CharField(required=False, default=str(uuid4()))
        scopes = serializers.CharField(
            required=False,
            help_text="Scope of the application separated by a comma.",
            default=["provider"],
        )
        app_owner = serializers.UUIDField(
            help_text="The owner for which the application is generated."
        )

    class CreationResponseSerializer(serializers.Serializer):
        client_id = serializers.CharField(help_text="Newly created Oauth app Client ID")
        client_secret = serializers.CharField(
            help_text="Newly created Oauth app Client Secret"
        )

    class RevocationRequestSerializer(serializers.Serializer):
        app_owner = serializers.UUIDField(
            help_text="The owner for which the application will be revoked."
        )
        delete = serializers.BooleanField(
            required=False,
            help_text="Indicate if the application should be removed or just revoked",
            default=False,
        )

    class RevokationResponseSerializer(utils.EmptyResponseSerializer):
        pass

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm("authent.add_accesstoken"):
            raise exceptions.PermissionDenied()

        serializer = self.CreationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        application = models.Application.objects.filter(
            owner=validated_data["app_owner"]
        ).last()

        if (
            application and application.scopes
        ):  # Application is revoked if there are no scopes
            serializer = self.CreationResponseSerializer(
                instance={
                    "client_id": application.client_id,
                    "client_secret": application.client_secret,
                }
            )

            return Response(serializer.data, status=200)

        application = public_api.create_application(
            name=validated_data["app_name"],
            scopes=validated_data["scopes"],
            owner=validated_data["app_owner"],
        )

        serializer = self.CreationResponseSerializer(
            instance={
                "client_id": application.client_id,
                "client_secret": application.client_secret,
            }
        )

        return Response(serializer.data, status=200)

    def delete(self, request, *args, **kwargs):
        if not request.user.has_perm("authent.add_accesstoken"):
            raise exceptions.PermissionDenied()

        serializer = self.RevocationRequestSerializer(data=request.data)
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

        if validated_data["delete"]:
            public_api.delete_application(validated_data["app_owner"])
        else:
            public_api.revoke_application(validated_data["app_owner"])

        return Response(self.RevokationResponseSerializer().data, status=200)


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

    class RevokeRequestSerializer(serializers.Serializer):
        access_token = serializers.CharField()

    class RevokeResponseSerializer(utils.EmptyResponseSerializer):
        pass

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

        token = public_api.get_long_lived_token(
            application, serializer.validated_data["token_duration"]
        )
        serializer = self.ResponseSerializer(
            instance={
                "access_token": token,
                "token_type": "bearer",
                "expires_in": validated_data["token_duration"],
            }
        )
        return Response(serializer.data, status=200)

    def delete(self, request, *args, **kwargs):
        if not request.user.has_perm("authent.add_accesstoken"):
            raise exceptions.PermissionDenied()

        serializer = self.RevokeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        token = models.AccessToken.objects.filter(
            token=validated_data["access_token"]
        ).last()

        if not token:
            raise exceptions.ValidationError(
                {
                    "token": _("No access token known for %s")
                    % validated_data["access_token"]
                }
            )

        if token.revoked_after:
            raise exceptions.ValidationError(
                {
                    "token": _("Token %s already revoked")
                    % validated_data["access_token"]
                }
            )

            public_api.revoke_long_lived_token(
                serializer.validated_data["access_token"]
            )
        return Response(self.RevokeResponseSerializer().data, status=200)
