# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0005_backend_public'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectBackend',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('project', models.CharField(max_length=255)),
                ('backend', models.ForeignKey(related_name='projects', to='db.Backend')),
            ],
            options={
                'verbose_name': 'Project-backend mappings.',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='projectbackend',
            unique_together=set([('project', 'backend')]),
        ),
    ]
