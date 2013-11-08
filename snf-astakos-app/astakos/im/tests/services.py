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

from astakos.im.tests.common import *
from snf_django.utils.testing import assertRaises


class RegisterTest(TestCase):
    def test_register(self):
        component1 = Component.objects.create(name="comp1")
        component2 = Component.objects.create(name="comp2")
        register.add_service(component1, "service1", "type1", [])
        register.add_service(component1, "service1a", "type1a", [])
        register.add_service(component2, "service2", "type2", [])

        resource = {"name": "service.resource",
                    "desc": "resource desc",
                    "service_type": "type1",
                    "service_origin": "service1"
                    }
        r, _ = register.add_resource(resource)
        self.assertEqual(r.service_type, "type1")

        resource = {"name": "service.resource",
                    "desc": "resource desc",
                    "service_type": "type2",
                    "service_origin": "service2"
                    }
        with assertRaises(register.RegisterException):
            r, _ = register.add_resource(resource)

        resource = {"name": "service.resource",
                    "desc": "resource desc",
                    "service_type": "type1a",
                    "service_origin": "service1a"
                    }
        r, _ = register.add_resource(resource)
        self.assertEqual(r.service_type, "type1a")
