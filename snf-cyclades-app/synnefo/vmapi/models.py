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

from logging import getLogger

from django.utils import simplejson as json
from django.core.urlresolvers import reverse

from synnefo.lib import join_urls

from synnefo.logic.servers import server_created
from synnefo.vmapi import backend, get_key, get_uuid, settings

log = getLogger('synnefo.vmapi')


def create_server_params(sender, created_vm_params, **kwargs):
    json_value = json.dumps(created_vm_params)
    uuid = get_uuid()
    key = get_key(uuid)
    log.info("Setting vmapi params with key %s for %s", key, sender)
    backend.set(key, json_value)

    path = reverse("vmapi_server_params", args=[uuid]).lstrip('/')
    config_url = join_urls(settings.BASE_HOST, path)
    # inject sender (vm) with its configuration url
    setattr(sender, 'config_url', config_url)
    return uuid

server_created.connect(create_server_params)
