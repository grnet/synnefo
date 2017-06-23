# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0006_add_projectbackend'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ipaddresshistory',
            name='network_id',
            field=models.IntegerField(verbose_name=b'Network', db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='ipaddresshistory',
            name='server_id',
            field=models.IntegerField(verbose_name=b'Server', db_index=True),
            preserve_default=True,
        ),
    ]
