# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('userdata', '0002_conflicting_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='publickeypair',
            name='created_at',
            field=models.DateTimeField(
                default=datetime.datetime(1970, 1, 1, 0, 0),
                auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='publickeypair',
            name='type',
            field=models.CharField(default=b'ssh', max_length=10),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='publickeypair',
            name='updated_at',
            field=models.DateTimeField(
                default=datetime.datetime(1970, 1, 1, 0, 0),
                auto_now=True),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='publickeypair',
            unique_together=set([('user', 'name')]),
        ),
    ]
