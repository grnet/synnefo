# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import json


def forward(apps, schema_editor):
    vms = apps.get_model('db', 'virtualmachine')
    db_alias = schema_editor.connection.alias
    for vm in vms.objects.using(db_alias).all():
        vm.key_names = json.dumps([vm.key_name] if vm.key_name is not None
                                  else [])
        vm.save()


def backward(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0006a_ipaddresshistory_indices'),
    ]

    operations = [
        migrations.AddField(
            model_name='virtualmachine',
            name='key_names',
            field=models.TextField(null=True, default='[]')
        ),
        migrations.RunPython(forward, backward)
    ]
