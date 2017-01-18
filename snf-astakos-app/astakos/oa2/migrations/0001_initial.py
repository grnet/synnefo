# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('im', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuthorizationCode',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.TextField()),
                ('redirect_uri', models.TextField(default=None, null=True)),
                ('scope', models.TextField(default=None, null=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime(2016, 6, 30, 14, 32, 48, 710897))),
                ('access_token', models.CharField(default=b'online', max_length=100, choices=[(b'online', 'Online token'), (b'offline', 'Offline token')])),
                ('state', models.TextField(default=None, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('identifier', models.CharField(unique=True, max_length=255)),
                ('secret', models.CharField(default=None, max_length=255, null=True)),
                ('url', models.CharField(max_length=255)),
                ('type', models.CharField(default=b'confidential', max_length=100, choices=[(b'confidential', 'Confidential'), (b'public', 'Public')])),
                ('is_trusted', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RedirectUrl',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_default', models.BooleanField(default=True)),
                ('url', models.TextField()),
                ('client', models.ForeignKey(to='oa2.Client', on_delete=django.db.models.deletion.PROTECT)),
            ],
            options={
                'ordering': ('is_default',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Token',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.TextField()),
                ('created_at', models.DateTimeField(default=datetime.datetime(2016, 6, 30, 14, 32, 48, 713704))),
                ('expires_at', models.DateTimeField()),
                ('token_type', models.CharField(default=b'Bearer', max_length=100, choices=[(b'Basic', 'Basic'), (b'Bearer', 'Bearer')])),
                ('grant_type', models.CharField(default=b'authorization_code', max_length=100, choices=[(b'authorization_code', 'Authorization code'), (b'password', 'Password'), (b'client_credentials', 'Client Credentials')])),
                ('redirect_uri', models.TextField()),
                ('scope', models.TextField(default=None, null=True)),
                ('access_token', models.CharField(default=b'online', max_length=100, choices=[(b'online', 'Online token'), (b'offline', 'Offline token')])),
                ('state', models.TextField(default=None, null=True)),
                ('client', models.ForeignKey(to='oa2.Client', on_delete=django.db.models.deletion.PROTECT)),
                ('user', models.ForeignKey(to='im.AstakosUser', on_delete=django.db.models.deletion.PROTECT)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='redirecturl',
            unique_together=set([('client', 'url')]),
        ),
        migrations.AddField(
            model_name='authorizationcode',
            name='client',
            field=models.ForeignKey(to='oa2.Client', on_delete=django.db.models.deletion.PROTECT),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='authorizationcode',
            name='user',
            field=models.ForeignKey(to='im.AstakosUser', on_delete=django.db.models.deletion.PROTECT),
            preserve_default=True,
        ),
    ]
