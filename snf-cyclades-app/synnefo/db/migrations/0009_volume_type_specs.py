# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0008_remove_key_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='VolumeTypeSpecs',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False,
                    auto_created=True, primary_key=True)),
                ('key', models.CharField(
                    max_length=64, verbose_name=b'Spec Key')),
                ('value', models.CharField(
                    max_length=255, verbose_name=b'Spec Value')),
                ('volume_type', models.ForeignKey(
                    related_name='specs', to='db.VolumeType')),
            ],
            options={
                'verbose_name': u'Volume type specs',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='volumetypespecs',
            unique_together=set([('key', 'volume_type')]),
        ),
    ]
