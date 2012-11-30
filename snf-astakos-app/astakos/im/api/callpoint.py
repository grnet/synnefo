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

from astakos.im.api.spec import AstakosAPI
from astakos.im.api.backends import get_backend

from synnefo.lib.commissioning import CorruptedError

from django.db import transaction

class AstakosCallpoint():

    api_spec = AstakosAPI()

#     http_exc_lookup = {
#         CorruptedError:   550,
#         InvalidDataError: 400,
#         InvalidKeyError:  401,
#         NoEntityError:    404,
#         NoQuantityError:  413,
#         NoCapacityError:  413,
#     }

    def init_connection(self, connection):
        if connection is not None:
            raise ValueError("Cannot specify connection args with %s" %
                             type(self).__name__)
        pass

    def commit(self):
        transaction.commit()

    def rollback(self):
        transaction.rollback()

    def do_make_call(self, call_name, data):
        call_fn = getattr(self, call_name, None)
        if not call_fn:
            m = "cannot find call '%s'" % (call_name,)
            raise CorruptedError(m)

        return call_fn(**data)

    def create_users(self, users=()):
        b = get_backend()
        rejected = (b.create_user(**u) for u in users)
        return rejected

    def update_users(self, users=()):
        b = get_backend()
        rejected = (b.update_user(**u) for u in users)
        return rejected

    def add_user_policies(self, user_id, update=False, policies=()):
        b = get_backend()
        rejected = b.add_policies(user_id, update, policies)
        return rejected

    def remove_user_policies(self, user_id, policies=()):
        b = get_backend()
        rejected = b.remove_policies(user_id, policies)
        return rejected

    def add_user_permissions(self, user_id, permissions=()):
        b = get_backend()
        rejected = b.add_permissions(user_id, permissions)
        return rejected

    def remove_user_permissions(self, user_id, permissions=()):
        b = get_backend()
        rejected = b.remove_permissions(user_id, permissions)
        return rejected

    def invite_users(self, sender_id, recipients=()):
        b = get_backend()
        rejected = b.invite_users(sender_id, recipients)
        return rejected

    def list_users(self, filter=()):
        b = get_backend()
        return b.list_users(filter)

    def get_user_status(self, user_id):
        b = get_backend()
        return b.get_resource_usage(user_id)

    def list_resources(self, filter=()):
        b = get_backend()
        return b.list_resources(filter)

    def add_services(self, services=()):
        b = get_backend()
        rejected = (b.create_service(**s) for s in services)
        return rejected

    def update_services(self, services=()):
        b = get_backend()
        rejected = (b.update_service(**s) for s in services)
        return rejected

    def remove_services(self, ids=()):
        b = get_backend()
        rejected = b.remove_services(ids)
        return rejected

    def add_resources(self, service_id, update=False, resources=()):
        b = get_backend()
        rejected = b.add_resources(service_id, update, resources)
        return rejected
    
    def remove_resources(self, service_id, ids=()):
        b = get_backend()
        rejected = b.remove_resources(service_id, ids)
        return rejected
    
    def create_groups(self, groups=()):
        b = get_backend()
        rejected = (b.create_group(**g) for g in groups)
        return rejected

API_Callpoint = AstakosCallpoint
