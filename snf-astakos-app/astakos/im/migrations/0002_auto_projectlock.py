# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.core.exceptions import ObjectDoesNotExist


class Migration(migrations.Migration):
    def create_project_lock(apps, schema_editor):
        ProjectLock = apps.get_model("im", "ProjectLock")
        try:
            ProjectLock.objects.get(id=1)
        except ObjectDoesNotExist:
            ProjectLock.objects.create(id=1)

    dependencies = [
        ('im', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_project_lock),
    ]
