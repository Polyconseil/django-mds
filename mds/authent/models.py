from django.contrib.postgres import fields as pg_fields
from django.db import models
from mds.models import Provider
from oauth2_provider.models import (
    AbstractApplication,
    AbstractAccessToken,
    AbstractGrant,
    AbstractRefreshToken,
)


class Application(AbstractApplication):
    owner = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Unique identifier for the owner of the application",
    )
    aggregator_for = models.ManyToManyField(
        Provider, help_text="Provider the application is allowed to write for"
    )
    scopes = pg_fields.ArrayField(
        models.CharField(max_length=32),
        help_text="Application allowed scopes (separated with commas)",
    )

    def natural_key(self):
        return (self.client_id,)

    @property
    def scopes_string(self):
        return " ".join(sorted(set(self.scopes)))


class AccessToken(AbstractAccessToken):
    token = models.TextField()  # remove 255 char limit (for JWT)
    jti = models.UUIDField(db_index=True)
    revoked_after = models.DateTimeField(null=True, blank=True)


class Grant(AbstractGrant):
    pass


class RefreshToken(AbstractRefreshToken):
    pass
