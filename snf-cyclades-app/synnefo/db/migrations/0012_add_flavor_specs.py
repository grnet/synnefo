# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0011_add_vm_flavor_related_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='FlavorSpecs',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID',
                    serialize=False,
                    auto_created=True,
                    primary_key=True)),
                ('key', models.CharField(
                    max_length=64,
                    verbose_name=b'Spec Key')),
                ('value', models.CharField(
                    max_length=255,
                    verbose_name=b'Spec Value')),
                ('flavor', models.ForeignKey(
                    related_name='specs',
                    to='db.Flavor')),
            ],
            options={
                'verbose_name': 'Flavor specs',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='flavorspecs',
            unique_together=set([('key', 'flavor')]),
        ),
    ]
