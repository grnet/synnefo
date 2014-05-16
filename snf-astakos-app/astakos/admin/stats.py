# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import datetime
from django.conf import settings
from django.db.models import Sum, Count

from astakos.im.models import AstakosUser, Resource
from astakos.quotaholder_app.models import Holding


def get_public_stats():
    users = AstakosUser.objects.all()
    active = users.filter(is_active=True)
    return {"users": {"total": users.count(),
                      "active": active.count()}}


def get_astakos_stats():
    stats = {"datetime": datetime.datetime.now().strftime("%c"),
             "providers": [],
             "users": {},
             "resources": {}}

    users = AstakosUser.objects.all()
    verified = users.filter(email_verified=True)
    active = users.filter(is_active=True)

    stats["users"]["all"] = {"total": users.count(),
                             "verified": verified.count(),
                             "active": active.count()}
    # Get all holdings from DB. Filter with 'source=None' in order to get
    # only the (base and user) projects, and not the user per project holdings
    holdings = Holding.objects.filter(source=None)\
                              .values("resource")\
                              .annotate(usage_sum=Sum("usage_max"),
                                        limit_sum=Sum("limit"))
    holdings = dict([(h["resource"], h) for h in holdings])

    resources_stats = {}
    for resource in Resource.objects.all():
        res_holdings = holdings.get(resource.name, {})
        resources_stats[resource.name] = {
            "used": res_holdings.get("usage_sum") or 0,
            "allocated": res_holdings.get("limit_sum") or 0,
            "unit": resource.unit,
            "description": resource.desc
        }
    stats["resources"]["all"] = resources_stats

    for provider in settings.ASTAKOS_IM_MODULES:
        # Add provider
        stats["providers"].append(provider)

        # Add stats about users
        users = AstakosUser.objects.filter(auth_providers__module=provider)
        verified = users.filter(email_verified=True)
        active = users.filter(is_active=True)
        exclusive = AstakosUser.objects.filter(email_verified=True,
                                               is_active=True)\
                               .annotate(num_providers=Count("auth_providers"))\
                               .filter(auth_providers__module=provider)\
                               .filter(num_providers=1)

        stats["users"][provider] = {"total": users.count(),
                                    "verified": verified.count(),
                                    "active": active.count(),
                                    "exclusive": exclusive.count()}

        # Add stats about resources
        users_uuids = exclusive.values_list("uuid", flat=True)
        # The 'holder' attribute contains user UUIDs prefixed with 'user:'
        users_uuids = ["user:" + uuid for uuid in users_uuids]
        resources_stats = {}
        for resource in Resource.objects.all():
            info = Holding.objects\
                          .filter(holder__in=users_uuids,
                                  resource=resource.name)\
                          .aggregate(usage_sum=Sum("usage_max"),
                                     limit_sum=Sum("limit"))
            resources_stats[resource.name] = {
                "used": info.get("usage_sum") or 0,
                "allocated": info.get("limit_sum") or 0,
                "unit": resource.unit,
                "description": resource.desc}
        stats["resources"][provider] = resources_stats

    return stats


if __name__ == "__main__":
    import json
    print json.dumps(get_astakos_stats())
