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

#import logging
from django.core.urlresolvers import reverse

from synnefo.db import models_factory as mf

from synnefo_admin import admin_settings
from synnefo_admin.admin.users.utils import get_suspended_vms
from .common import AdminTestCase


class TestAdminUsers(AdminTestCase):

    """Test suite for user-related tests."""

    def expected_href(self, pk):
        """Create an href string for a vm with the provided pk."""
        vm_details = reverse('admin-details', args=['vm', pk])
        return '<a href={0}>Name{1} (id:{1})</a>'.format(vm_details, pk)

    def test_suspended_vms(self):
        """Test if suspended VMs for a user are displayed properly."""
        # The VMs that will be shown at any time to the user will be between
        # the ID 1134 and (1134 + limit).
        start = 1134
        end = start + admin_settings.ADMIN_LIMIT_SUSPENDED_VMS_IN_SUMMARY

        # Test 1 - Assert that 'None' is displayed when there are no suspended
        # VMs.
        vms = get_suspended_vms(self.user)
        self.assertEqual(vms, 'None')

        # Test 2 - Assert that only one href is printed when there is only one
        # suspended VM.
        mf.VirtualMachineFactory(userid=self.user.uuid, pk=start,
                                 name='Name{}'.format(start),
                                 suspended=True)
        vms = get_suspended_vms(self.user)
        self.assertEqual(vms, self.expected_href(start))

        # Test 3 - Assert that the hrefs are comma-separated when there are
        # more than one suspended VMs.
        #
        # Create one more VM, get the list of suspended VMs and split it.
        mf.VirtualMachineFactory(userid=self.user.uuid, pk=start + 1,
                                 name='Name{}'.format(start + 1),
                                 suspended=True)
        vms = get_suspended_vms(self.user).split(', ')

        # Asssert that each element of the list is displayed properly.
        for pk in range(start, start + 1):
            i = pk - start
            self.assertEqual(vms[i], self.expected_href(pk))

        # Test 4 - Assert that dots ('...') are printed when there are too
        # many suspended VMs.
        #
        # Create more VMs than the current limit and split them like before.
        for pk in range(start + 2, end + 1):
            mf.VirtualMachineFactory(userid=self.user.uuid, pk=pk,
                                     name='Name{}'.format(pk), suspended=True)
        vms = get_suspended_vms(self.user).split(', ')

        # Asssert that each element of the list is displayed properly and that
        # the last element is actually dots ('...').
        for pk in range(start, end + 1):
            i = pk - start
            if pk == end:
                self.assertEqual(vms[i], '...')
            else:
                self.assertEqual(vms[i], self.expected_href(pk))
