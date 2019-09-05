# Generated by Django 2.1.11 on 2019-09-09 14:34

import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('mds', '0043_policy'),
    ]

    operations = [
        migrations.CreateModel(
            name='Compliance',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('rule', models.UUIDField(default=uuid.uuid4)),
                ('geography', models.UUIDField(default=uuid.uuid4)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='policy',
            name='prev_policies',
            field=models.ManyToManyField(blank=True, related_name='_policy_prev_policies_+', to='mds.Policy'),
        ),
        migrations.AlterField(
            model_name='policy',
            name='providers',
            field=models.ManyToManyField(blank=True, to='mds.Provider'),
        ),
        migrations.AlterField(
            model_name='policy',
            name='rules',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=list, encoder=django.core.serializers.json.DjangoJSONEncoder),
        ),
        migrations.AddField(
            model_name='compliance',
            name='policy',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='compliances', to='mds.Policy'),
        ),
        migrations.AddField(
            model_name='compliance',
            name='vehicle',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='compliances', to='mds.Device'),
        ),
    ]
