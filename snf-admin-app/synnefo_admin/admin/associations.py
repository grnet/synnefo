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

from synnefo_admin.admin.utils import get_actions


class AdminAssociation(object):

    """Generic class for associated items.

    Association items have the following fields:

        * list: The associated items,
        * type: The type of the items

    and the following optional fields:

        * actions: A dictionary with the permitted actions for *all* the items
        * total: How many items are in total
        * excluded: How many items are excluded
        * showing: How many items are shown
    """

    def __init__(self, request, items, type, actions=None, total=0,
                 excluded=0, showing=0):
        self.items = items
        self.type = type

        if actions:
            self.actions = actions
        else:
            self.actions = get_actions(type, request.user)

        if total != 0:
            self.total = total
        elif hasattr(self, 'count_total'):
            self.total = self.count_total()
        else:
            self.total = self.count_items()

        self.excluded = excluded
        self.showing = total

    def count_items(self):
        return len(self.items)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return (u"<%s association, total: %s, excluded: %s, showing: %s, items: %s>" %
                (self.type.capitalize(), self.total, self.excluded,
                 self.showing, self.items))


class AdminQuerySetAssociation(AdminAssociation):

    def count_total(self):
        return self.items.count()

    @property
    def qs(self):
        return self.items

    @qs.setter
    def qs(self, value):
        self.items = value

    def __unicode__(self):
        return (u"<%s association, total: %s, excluded: %s, showing: %s, qs: %s>" %
                (self.type.capitalize(), self.total, self.excluded,
                 self.showing, self.qs))


class AdminSimpleAssociation(AdminAssociation):
    pass


class UserAssociation(AdminQuerySetAssociation):
    def __init__(self, request, items, **kwargs):
        AdminAssociation.__init__(self, request, items, type='user', **kwargs)


class QuotaAssociation(AdminSimpleAssociation):
    def __init__(self, request, items, **kwargs):
        AdminAssociation.__init__(self, request, items, type='quota', **kwargs)


class VMAssociation(AdminQuerySetAssociation):
    def __init__(self, request, items, **kwargs):
        AdminAssociation.__init__(self, request, items, type='vm', **kwargs)


class SimpleVMAssociation(AdminSimpleAssociation):
    def __init__(self, request, items, **kwargs):
        AdminAssociation.__init__(self, request, items, type='vm', **kwargs)


class VolumeAssociation(AdminQuerySetAssociation):
    def __init__(self, request, items, **kwargs):
        AdminAssociation.__init__(self, request, items, type='volume', **kwargs)


class NetworkAssociation(AdminQuerySetAssociation):
    def __init__(self, request, items, **kwargs):
        AdminAssociation.__init__(self, request, items, type='network', **kwargs)


class SimpleNetworkAssociation(AdminSimpleAssociation):
    def __init__(self, request, items, **kwargs):
        AdminAssociation.__init__(self, request, items, type='network', **kwargs)


class NicAssociation(AdminQuerySetAssociation):
    def __init__(self, request, items, **kwargs):
        AdminAssociation.__init__(self, request, items, type='nic', **kwargs)


class SimpleNicAssociation(AdminSimpleAssociation):
    def __init__(self, request, items, **kwargs):
        AdminAssociation.__init__(self, request, items, type='nic', **kwargs)


class IPAssociation(AdminQuerySetAssociation):
    def __init__(self, request, items, **kwargs):
        AdminAssociation.__init__(self, request, items, type='ip', **kwargs)


class IPLogAssociation(AdminQuerySetAssociation):

    order_by = 'allocated_at'

    def __init__(self, request, items, **kwargs):
        AdminAssociation.__init__(self, request, items, type='ip_log', **kwargs)


class ProjectAssociation(AdminQuerySetAssociation):
    def __init__(self, request, items, **kwargs):
        AdminAssociation.__init__(self, request, items, type='project', **kwargs)
