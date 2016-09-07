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


from django.core.exceptions import ObjectDoesNotExist

from astakos.im.models import AstakosUser
from synnefo.db.models import VirtualMachine

from synnefo_admin.admin.exceptions import AdminHttp404
from synnefo_admin.admin.utils import create_details_href


def get_vm_or_404(query, for_update=False):
    vm_obj = VirtualMachine.objects.select_for_update() if for_update\
        else VirtualMachine.objects
    try:
        return vm_obj.get(pk=int(query))
    except (ObjectDoesNotExist, ValueError):
        raise AdminHttp404(
            "No VM was found that matches this query: %s\n" % query)


def get_flavor_info(vm):
    return ('CPU: x' + str(vm.flavor.cpu) + ', RAM: ' + str(vm.flavor.ram) +
            'MB, Disk size: ' + str(vm.flavor.disk) + 'GB, Disk template: ' +
            str(vm.flavor.volume_type.disk_template))


def get_user_details_href(vm):
    user = AstakosUser.objects.get(uuid=vm.userid)
    return create_details_href('user', user.realname, user.email, user.uuid)
