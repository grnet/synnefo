# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('im', '0003_remove_invalid_local'),
    ]

    operations = [
        migrations.AlterField(
            model_name='astakosuserauthprovider',
            name='identifier',
            field=models.CharField(default=b'', max_length=255,
                                   verbose_name='Third-party identifier',
                                   blank=True, null=False),
            preserve_default=True,
        ),
    ]
