# Generated by Django 2.1.10 on 2019-07-23 17:26

from django.db import migrations


def fill_provider_configuration(apps, schema_editor):
    Provider = apps.get_model("mds", "Provider")

    for provider in Provider.objects.all():
        prev_api_config = provider.api_configuration
        prev_start_time_field = prev_api_config.get("start_time_field", "start_time")

        # First, we update the api_configuration
        provider.api_configuration["polling_cursor"] = prev_start_time_field
        if provider.api_configuration.get("start_time_field"):
            del provider.api_configuration["start_time_field"]

        # Next, we update the timestamp of the cursor fields
        if prev_start_time_field == "start_time":
            provider.last_event_time_polled = provider.last_start_time_polled
        elif prev_start_time_field == "start_recorded":
            provider.last_recorded_polled = provider.last_start_time_polled

        provider.save(
            update_fields=[
                "api_configuration",
                "last_event_time_polled",
                "last_recorded_polled",
            ]
        )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [("mds", "0035_pre_add_fields")]

    operations = [
        migrations.RunPython(fill_provider_configuration, migrations.RunPython.noop)
    ]
