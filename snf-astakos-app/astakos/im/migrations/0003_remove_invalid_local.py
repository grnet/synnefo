# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db.models import Count


def _partition_by(f, l):
    d = {}
    for x in l:
        group = f(x)
        group_l = d.get(group, [])
        group_l.append(x)
        d[group] = group_l
    return d


def fix_user_local_providers(providers):

    print('\nFound {0} local auth providers for user {1}. Will keep provider'
          ' id={2}'.format(len(providers),
                           providers[0].user.uuid, providers[0].id))
    for idx, lp in enumerate(providers[1:]):
        print('Deleting Provider id={0}: active={1}, auth_backend={2}, '
              ' info_data={3}, created={4}, last_login_at={5}'.format(
                lp.id, lp.active, lp.auth_backend, lp.info_data,
                lp.created, lp.last_login_at))
        lp.delete()


class Migration(migrations.Migration):

    def forward(apps, schema_editor):
        AstakosUser = apps.get_model("im", "AstakosUser")
        affected_users = AstakosUser.objects\
            .filter(auth_providers__module='local')\
            .annotate(local_cnt=Count('auth_providers'))\
            .filter(local_cnt__gte=2)

        AuthProvider = apps.get_model("im", "AstakosUserAuthProvider")
        providers = AuthProvider.objects\
            .filter(module='local', user__in=affected_users)\
            .order_by('user', '-active', '-created')

        for user_providers in _partition_by(
                lambda p: p.user, providers).values():
            fix_user_local_providers(user_providers)

    def backward(apps, schema_editor):
        pass

    dependencies = [
        ('im', '0002_auto_projectlock'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
