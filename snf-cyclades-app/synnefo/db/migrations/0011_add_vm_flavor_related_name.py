# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0010_add_flavoraccess'),
    ]

    operations = [
        migrations.AlterField(
            model_name='virtualmachine',
            name='flavor',
            field=models.ForeignKey(related_name='virtual_machines', on_delete=django.db.models.deletion.PROTECT, to='db.Flavor'),
            preserve_default=True,
        ),
    ]
