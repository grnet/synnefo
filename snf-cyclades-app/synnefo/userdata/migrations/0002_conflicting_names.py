# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.db.models import Count
import string

TAG = "_"
SUFFIXES = [""] + list(string.ascii_lowercase)


def decide_name(conflicting_name, occurrence, existing_names):
    name_constructor = conflicting_name + TAG + str(occurrence - 1)
    for suffix in SUFFIXES:
        name = name_constructor + suffix
        if name not in existing_names:
            return name
    raise ValueError("Cannot decide unique name for '%s'." % conflicting_name)


def migrate_conflicting_names(apps, schema_editor):
    PublicKeyPair = apps.get_model("userdata", "PublicKeyPair")
    conflicts = PublicKeyPair.objects.values("user", "name").\
        annotate(count=Count("id")).filter(count__gt=1)

    for conflict in conflicts:
        user = conflict["user"]
        conflicting_name = conflict["name"]
        user_keys = PublicKeyPair.objects.filter(user=user).order_by("id")
        all_names = set(key.name for key in user_keys)
        occurrence = 0
        for key in user_keys:
            if key.name != conflicting_name:
                continue
            occurrence += 1
            if occurrence == 1:
                print "Preserved key '%s' (of user '%s') name '%s'." % (
                    key.id, key.user, key.name)
                continue
            new_name = decide_name(conflicting_name, occurrence, all_names)
            key.name = new_name
            key.save()
            all_names.add(new_name)
            print "Renamed key %s (of user '%s') from '%s' to '%s'." % (
                key.id, key.user, conflicting_name, new_name)


class Migration(migrations.Migration):

    dependencies = [
        ('userdata', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_conflicting_names),
    ]
