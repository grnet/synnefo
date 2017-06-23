# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0004_virtualmachine_key_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='backend',
            name='public',
            field=models.BooleanField(default=True, verbose_name=b'Public'),
            preserve_default=False,
        ),
    ]
