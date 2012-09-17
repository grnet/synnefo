# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

import socket
import logging
import itertools

from functools import wraps
from itertools import tee

from django.utils.translation import ugettext as _

from astakos.im.settings import QUOTA_HOLDER_URL, LOGGING_LEVEL

if QUOTA_HOLDER_URL:
    from commissioning.clients.quotaholder import QuotaholderHTTP

ENTITY_KEY = '1'

logger = logging.getLogger(__name__)


def call(func_name):
    """Decorator function for QuotaholderHTTP client calls."""
    def decorator(payload_func):
        @wraps(payload_func)
        def wrapper(entities=(), client=None, **kwargs):
            if not entities:
                return ()
        
            if not QUOTA_HOLDER_URL:
                return ()
        
            c = client or QuotaholderHTTP(QUOTA_HOLDER_URL)
            func = c.__dict__.get(func_name)
            if not func:
                return c,
            
            data = payload_func(entities, client, **kwargs)
            if not data:
                return c,
            
            funcname = func.__name__
            kwargs = {'context': {}, funcname: data}
            rejected = func(**kwargs)
            msg = _('%s: %s - Rejected: %s' % (funcname, data, rejected,))
            logger.log(LOGGING_LEVEL, msg)
            return c, rejected
        return wrapper
    return decorator

@call('set_quota')
def send_quota(users, client=None):
    data = []
    append = data.append
    for user in users:
        for resource, limit in user.quota.iteritems():
            key = ENTITY_KEY
            quantity = None
            capacity = limit
            import_limit = None
            export_limit = None
            flags = 0
            args = (user.email, resource, key, quantity, capacity, import_limit,
                    export_limit, flags)
            append(args)
    return data


@call('set_quota')
def send_resource_quantities(resources, client=None):
    data = []
    append = data.append
    for resource in resources:
        key = ENTITY_KEY
        quantity = resource.meta.filter(key='quantity') or None
        capacity = None
        import_limit = None
        export_limit = None
        flags = 0
        args = (resource.service, resource, key, quantity, capacity,
                import_limit, export_limit, flags)
        append(args)
    return data


@call('get_quota')
def get_quota(users, client=None):
    data = []
    append = data.append
    for user in users:
        try:
            entity = user.email
        except AttributeError:
            continue
        else:
            for r in user.quota.keys():
                args = entity, r, ENTITY_KEY
                append(args)
    return data


@call('create_entity')
def create_entities(entities, client=None, field=''):
    data = []
    append = data.append
    for entity in entities:
        try:
            entity = entity.__getattribute__(field)
        except AttributeError:
            continue
        owner = 'system'
        key = ENTITY_KEY
        ownerkey = ''
        args = entity, owner, key, ownerkey
        append(args)
    return data


def register_users(users, client=None):
    users, copy = itertools.tee(users)
    client, rejected = create_entities(entities=users,
                                       client=client,
                                       field='email')
    created = (e for e in copy if unicode(e) not in rejected)
    return send_quota(created, client)


def register_resources(resources, client=None):
    resources, copy = itertools.tee(resources)
    client, rejected = create_entities(entities=resources,
                                       client=client,
                                       field='service')
    created = (e for e in copy if unicode(e) not in rejected)
    return send_resource_quantities(created, client)