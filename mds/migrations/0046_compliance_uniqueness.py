# Generated by Django 2.2 on 2019-09-23 11:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mds', '0045_add_fixed_price_on_policy_model'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='compliance',
            unique_together={('policy', 'rule', 'geography', 'vehicle', 'start_date')},
        ),
    ]
