# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0014_vm_rescue_properties'),
    ]

    operations = [
        migrations.CreateModel(
            name='VirtualMachineTag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tag', models.CharField(max_length=60)),
                ('status', models.CharField(default=b'PENDADD', max_length=30, choices=[(b'PENDADD', b'Pending addition'), (b'ACTIVE', b'Active')])),
                ('vm', models.ForeignKey(related_name='tags', to='db.VirtualMachine')),
            ],
            options={
                'verbose_name': 'Tag for a VM.',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='virtualmachinetag',
            unique_together=set([('vm', 'tag')]),
        ),
    ]
