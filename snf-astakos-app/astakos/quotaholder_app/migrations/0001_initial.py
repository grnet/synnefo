# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Commission',
            fields=[
                ('serial', models.AutoField(serialize=False, primary_key=True)),
                ('name', models.CharField(default=b'', max_length=4096)),
                ('clientkey', models.CharField(max_length=4096)),
                ('issue_datetime', models.DateTimeField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Holding',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('holder', models.CharField(max_length=4096, db_index=True)),
                ('source', models.CharField(max_length=4096, null=True)),
                ('resource', models.CharField(max_length=4096)),
                ('limit', models.BigIntegerField()),
                ('usage_min', models.BigIntegerField(default=0)),
                ('usage_max', models.BigIntegerField(default=0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Provision',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('holder', models.CharField(max_length=4096, db_index=True)),
                ('source', models.CharField(max_length=4096, null=True)),
                ('resource', models.CharField(max_length=4096)),
                ('quantity', models.BigIntegerField()),
                ('serial', models.ForeignKey(related_name='provisions', to='quotaholder_app.Commission')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProvisionLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('serial', models.BigIntegerField()),
                ('name', models.CharField(max_length=4096)),
                ('issue_time', models.CharField(max_length=4096)),
                ('log_time', models.CharField(max_length=4096)),
                ('holder', models.CharField(max_length=4096)),
                ('source', models.CharField(max_length=4096, null=True)),
                ('resource', models.CharField(max_length=4096)),
                ('limit', models.BigIntegerField()),
                ('usage_min', models.BigIntegerField()),
                ('usage_max', models.BigIntegerField()),
                ('delta_quantity', models.BigIntegerField()),
                ('reason', models.CharField(max_length=4096)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='holding',
            unique_together=set([('holder', 'source', 'resource')]),
        ),
    ]
