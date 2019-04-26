# Generated by Django 2.1.4 on 2019-01-22 22:55

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import oauth2_provider.generators


class Migration(migrations.Migration):

    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="AccessToken",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("expires", models.DateTimeField()),
                ("scope", models.TextField(blank=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                ("token", models.TextField()),
                ("jti", models.UUIDField(db_index=True)),
                ("revoked_after", models.DateTimeField(null=True)),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="Application",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "client_id",
                    models.CharField(
                        db_index=True,
                        default=oauth2_provider.generators.generate_client_id,
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    "redirect_uris",
                    models.TextField(
                        blank=True, help_text="Allowed URIs list, space separated"
                    ),
                ),
                (
                    "client_type",
                    models.CharField(
                        choices=[
                            ("confidential", "Confidential"),
                            ("public", "Public"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "authorization_grant_type",
                    models.CharField(
                        choices=[
                            ("authorization-code", "Authorization code"),
                            ("implicit", "Implicit"),
                            ("password", "Resource owner password-based"),
                            ("client-credentials", "Client credentials"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "client_secret",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default=oauth2_provider.generators.generate_client_secret,
                        max_length=255,
                    ),
                ),
                ("name", models.CharField(blank=True, max_length=255)),
                ("skip_authorization", models.BooleanField(default=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.UUIDField(
                        db_index=True,
                        help_text="Unique identifier for the owner of the application",
                        null=True,
                    ),
                ),
                (
                    "scopes",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=32),
                        help_text="Application allowed scopes.",
                        size=None,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="authent_application",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="Grant",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=255, unique=True)),
                ("expires", models.DateTimeField()),
                ("redirect_uri", models.CharField(max_length=255)),
                ("scope", models.TextField(blank=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="authent.Application",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="authent_grant",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="RefreshToken",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("token", models.CharField(max_length=255)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                ("revoked", models.DateTimeField(null=True)),
                (
                    "access_token",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="refresh_token",
                        to="authent.AccessToken",
                    ),
                ),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="authent.Application",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="authent_refreshtoken",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.AddField(
            model_name="accesstoken",
            name="application",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="authent.Application",
            ),
        ),
        migrations.AddField(
            model_name="accesstoken",
            name="source_refresh_token",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="refreshed_access_token",
                to="authent.RefreshToken",
            ),
        ),
        migrations.AddField(
            model_name="accesstoken",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="authent_accesstoken",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="refreshtoken", unique_together={("token", "revoked")}
        ),
    ]
