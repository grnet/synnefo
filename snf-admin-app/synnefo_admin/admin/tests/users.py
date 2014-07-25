# -*- coding: utf-8 -*-
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

from astakos.im.models import ProjectMembership, Resource
from astakos.im.functions import remove_membership, enroll_member
from synnefo.db import models_factory as mf

from synnefo_admin import admin_settings
from synnefo_admin.admin.users.utils import get_suspended_vms, get_quotas
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

    def test_quota(self):
        """Test if quotas are displayed properly for a user."""
        def get_project_id(obj):
            """Sort by project id."""
            return obj['project'].uuid

        def assertQuotaEqual(quota1, quota2):
            """Custom assert function fro quota lists."""
            quota1 = sorted(quota1, key=get_project_id)
            quota2 = sorted(quota2, key=get_project_id)
            self.assertEqual(len(quota1), len(quota2))

            for q1, q2 in zip(quota1, quota2):
                p1 = q1['project']
                p2 = q2['project']
                r1 = q1['resources']
                r2 = q2['resources']
                self.assertEqual(p1.uuid, p2.uuid)
                self.assertItemsEqual(r1, r2)

        # Get the reported description of the resources.
        resource = Resource.objects.get(name=u"σέρβις1.ρίσορς11")
        desc11 = resource.report_desc
        resource = Resource.objects.get(name=u"σέρβις1.resource12")
        desc12 = resource.report_desc
        resource = Resource.objects.get(name=u"astakos.pending_app")
        desc13 = resource.report_desc

        # These should be the base quota of the user
        base_quota = [{'project': self.user.base_project,
                       'resources': [(desc11, '0', '100'),
                                     (desc13, '0', '3'),
                                     (desc12, '0 bytes', '1.00 kB')]
                       }]

        # Test 1 - Check if get_quotas works properly for base quotas
        quota = get_quotas(self.user)
        assertQuotaEqual(quota, base_quota)

        # Test 2 - Check if get_quotas works properly for projects too.
        #
        # Add member to a project
        enroll_member(self.project.uuid, self.user)

        # These should be the additional quota from the project.
        new_quota = [{'project': self.project,
                      'resources': [(desc11, '0', '512')]
                      }]

        # Assert that get_quotas works as intented
        quota = get_quotas(self.user)
        assertQuotaEqual(new_quota + base_quota, quota)

        # Test 3 - Check if get_quotas shows zero values for removed member
        # from a project.
        #
        # Remove member from project
        membership = ProjectMembership.objects.get(project=self.project,
                                                   person=self.user)
        remove_membership(membership.id)

        # These should be the new quota from the project. They are zero since
        # the user has not used any of the resources, but they are still
        # displayed as the project limit is > 0.
        new_quota = [{'project': self.project,
                      'resources': [(desc11, '0', '0')]
                      }]

        # Assert that get_quotas works as intented
        quota = get_quotas(self.user)
        assertQuotaEqual(new_quota + base_quota, quota)
