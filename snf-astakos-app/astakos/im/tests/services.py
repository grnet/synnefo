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
