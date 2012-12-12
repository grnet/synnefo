# encoding: utf-8

# Copyright 2012 GRNET S.A. All rights reserved.
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

from astakos.im.models import Service, Resource
from django.core.management.base import BaseCommand, CommandError
import logging

logger = logging.getLogger(__name__)

def create_service_resources(service_name, service_dict):
    url = service_dict.get('url')
    resources = service_dict.get('resources') or ()
    service, created = Service.objects.get_or_create(
        name=service_name,
        defaults={'url': url}
    )

    for r in resources:
        try:
            resource_name = r.pop('name', '')
            uplimit = r.pop('uplimit', None)
            r, created = Resource.objects.get_or_create(
                service=service,
                name=resource_name,
                defaults=r)
        except Exception, e:
            print "Cannot create resource ", resource_name
            continue

class Command(BaseCommand):
    args = ""
    help = "Register service resources"

    def handle(self, *args, **options):
        from astakos.im.settings import SERVICES
        for k, v in SERVICES.iteritems():
            create_service_resources(k, v)

