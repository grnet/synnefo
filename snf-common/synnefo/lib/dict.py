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

from collections import OrderedDict


class SnfOrderedDict(OrderedDict):

    """Class that combines a data structure and a list into an OrderedDict.

    Given a data structure (class/dict) and list, create a list of tuples.
    Then, use the Python's 2.7 OrderedDict constructor, which expects a list of
    key-value pairs, in order to create the OrderedDict.
    """

    def __init__(self, data=None, lst=None, strict=True):
        """Combine a data structure and a list into a list of tuples.

        This __init__ function will default to the __init__ function of
        OrderedDict, if only one argument is passed.

        By default, the items in the list must correspond to the keys in the
        provided data structure. To relax this requirement, set the `strict`
        argument to False.
        """
        if lst is None:
            return super(SnfOrderedDict, self).__init__(data)

        self.__strict = strict

        # Use the appropriate constructor, depending on the data structure
        # type, to create the required list of tuples.
        if isinstance(data, dict):
            tpl = self.fromdict_constructor(data, lst)
        else:
            tpl = self.fromclass_constructor(data, lst)

        # Call the __init__ function of the OrderedDict class with the tuple
        # as argument
        return super(SnfOrderedDict, self).__init__(tpl)

    def fromdict_constructor(self, dct, lst):
        """Create a list of tuples from a dict and a list."""
        new_lst = []
        for item in lst:
            try:
                new_lst.append((item, dct[item]))
            except KeyError:
                if self.__strict:
                    raise
        return new_lst

    def fromclass_constructor(self, cls, lst):
        """Create a list of tuples from any class and a list."""
        new_lst = []
        for item in lst:
            try:
                new_lst.append((item, getattr(cls, item)))
            except AttributeError:
                if self.__strict:
                    raise
        return new_lst
