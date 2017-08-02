# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    def forward(apps, schema_editor):
        VirtualMachine = apps.get_model("db", "VirtualMachine")
        RescueProperties = apps.get_model("db", "RescueProperties")
        Image = apps.get_model("db", "Image")

        for vm in VirtualMachine.objects.filter(deleted=False):
            try:
                vm_image = Image.objects.get(uuid=vm.imageid)
            except VirtualMachine.DoesNotExist as e:
                print("Image %d for vm %d could not be found. Using default "
                      "properties" % (vm.imageid, vm.id))
                ri = RescueProperties(os='', os_family='')
            else:
                ri = RescueProperties(os=vm_image.os,
                                      os_family=vm_image.osfamily)
            ri.save()
            vm.rescue_properties = ri
            vm.save()

    def backward(apps, schema_editor):
        pass

    dependencies = [
        ('db', '0013_vm_rescue'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
