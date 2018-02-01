# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def set_user_default_project(apps, schema_editor):
    AstakosUser = apps.get_model('im', 'AstakosUser')
    AstakosUser.objects.update(default_project=models.F('uuid'))


class Migration(migrations.Migration):

    dependencies = [
        ('im', '0005_astakosuser_default_project'),
    ]

    operations = [
        migrations.RunPython(set_user_default_project),
    ]
