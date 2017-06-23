# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='IPAddressHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address', models.CharField(max_length=64, verbose_name=b'IP Address', db_index=True)),
                ('server_id', models.IntegerField(verbose_name=b'Server')),
                ('network_id', models.IntegerField(verbose_name=b'Network')),
                ('user_id', models.CharField(max_length=128, verbose_name=b'IP user', db_index=True)),
                ('action', models.CharField(max_length=255, verbose_name=b'Action')),
                ('action_date', models.DateTimeField(default=datetime.datetime.now, verbose_name=b'Datetime of IP action')),
                ('action_reason', models.CharField(default=b'', max_length=1024, verbose_name=b'Action reason')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
