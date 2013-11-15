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

"""
This is the burnin class that tests the Astakos functionality

"""

from kamaki.clients.compute import ComputeClient
from kamaki.clients import ClientError

from synnefo_tools.burnin import common


# Too many public methods (47/20). pylint: disable-msg=R0904
class AstakosTestCase(common.BurninTests):
    """Test Astakos functionality"""
    def test_unauthorized_access(self):
        """Test access without a valid token fails"""
        false_token = "12345"
        client = ComputeClient(self.clients.compute_url, false_token)
        client.CONNECTION_RETRY_LIMIT = self.clients.retry

        with self.assertRaises(ClientError) as cl_error:
            client.list_servers()
            self.assertEqual(cl_error.exception.status, 401)


class AstakosFoo(common.BurninTests):
    """Just Fail"""
    def test_just_foo(self):
        """A test that just fails"""
        self.fail("just fail")
