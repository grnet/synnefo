# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('im', '0004_fix_auth_provider_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='astakosuser',
            name='default_project',
            field=models.CharField(max_length=255, null=True),
            preserve_default=True,
        ),
    ]
