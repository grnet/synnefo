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

from astakos.im.settings import BACKEND_BLOCK_MODULE, BACKEND_BLOCK_PATH, BACKEND_DB_CONNECTION, BACKEND_DB_MODULE, BACKEND_QUOTA, BACKEND_VERSIONING

from pithos.backends import connect_backend

def get_backend():
    backend = connect_backend(db_module=BACKEND_DB_MODULE,
                              db_connection=BACKEND_DB_CONNECTION,
                              block_module=BACKEND_BLOCK_MODULE,
                              block_path=BACKEND_BLOCK_PATH)
    backend.default_policy['quota'] = BACKEND_QUOTA
    backend.default_policy['versioning'] = BACKEND_VERSIONING
    return backend

def get_quota(user):
    backend = get_backend()
    quota = backend.get_account_policy(user, user)['quota']
    backend.close()
    return quota

def set_quota(user, quota):
    backend = get_backend()
    backend.update_account_policy(user, user, {'quota': quota})
    backend.close()
    return quota
