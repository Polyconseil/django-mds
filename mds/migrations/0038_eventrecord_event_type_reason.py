# Generated by Django 2.1.11 on 2019-08-16 14:14

from django.db import migrations
import mds.models


class Migration(migrations.Migration):

    dependencies = [("mds", "0037_remove_provider_last_start_time_polled")]

    operations = [
        migrations.AddField(
            model_name="eventrecord",
            name="event_type_reason",
            field=mds.models.UnboundedCharField(
                blank=True,
                choices=[
                    ("low_battery", "Low battery"),
                    ("maintenance", "Maintenance"),
                    ("compliance", "Compliance"),
                    ("off_hours", "Off hours"),
                    ("rebalance", "Rebalance"),
                    ("charge", "Charge"),
                    ("missing", "Missing"),
                    ("decommissioned", "Decommissioned"),
                ],
                null=True,
            ),
        )
    ]