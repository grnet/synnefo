# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import json


def forward(apps, schema_editor):
    pass


def backward(apps, schema_editor):
    vms = apps.get_model('db', 'virtualmachine')
    db_alias = schema_editor.connection.alias
    for vm in vms.objects.using(db_alias).all():
        # Ensure string is json encoded
        try:
            key_names = json.loads(vm.key_names)
            if key_names:
                vm.key_name = key_names[0]
                vm.save()
        except ValueError:
            print "Warning key_names field of VM %s contains invalid data: %s" % (vm.name, vm.key_name)


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0007_add_snf_key_names'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
        migrations.RemoveField(
            model_name='virtualmachine',
            name='key_name',
        ),
    ]
