# Copyright 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.
import datetime
from django.conf import settings
from django.db.models import Sum

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

    for provider in settings.ASTAKOS_IM_MODULES:
        # Add provider
        stats["providers"].append(provider)

        # Add stats about users
        users = AstakosUser.objects.filter(auth_providers__module=provider)
        verified = users.filter(email_verified=True)
        active = users.filter(is_active=True)

        stats["users"][provider] = {"total": users.count(),
                                    "verified": verified.count(),
                                    "active": active.count()}

        # Add stats about resources
        users_uuids = users.values_list("uuid", flat=True)
        resources_stats = {}
        for resource in Resource.objects.all():
            info = Holding.objects\
                          .filter(holder__in=users_uuids,
                                  resource=resource.name)\
                          .aggregate(usage_sum=Sum("usage_max"),
                                     limit_sum=Sum("limit"))
            resources_stats[resource.name] = {"used": info["usage_sum"],
                                              "limit": info["limit_sum"],
                                              "unit": resource.unit,
                                              "description": resource.desc}
        stats["resources"][provider] = resources_stats

    return stats
