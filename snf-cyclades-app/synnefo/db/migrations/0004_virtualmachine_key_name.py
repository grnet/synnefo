# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0003_auto_ip_ownership'),
    ]

    operations = [
        migrations.AddField(
            model_name='virtualmachine',
            name='key_name',
            field=models.CharField(max_length=100, null=True),
            preserve_default=True,
        ),
    ]
