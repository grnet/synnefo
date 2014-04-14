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

import sys
import pkg_resources
import types
import os

from collections import defaultdict

# List of python distribution names which entry points will get excluded
# from snf-common settings extension mechanism
EXCLUDED_PACKAGES = os.environ.get('SYNNEFO_EXCLUDE_PACKAGES', '').split(":")


def get_entry_points(ns, name):
    for entry_point in pkg_resources.iter_entry_points(group=ns):
        if entry_point.name == name and \
                not entry_point.dist.project_name in EXCLUDED_PACKAGES:
            yield entry_point


def extend_module(module_name, attrs):
    module = sys.modules[module_name]
    for k, v in attrs.iteritems():
        setattr(module, k, v)


def entry_point_to_object(ep):
    object_or_func = ep.load()

    # user defined entry point is a function
    # get the return value
    obj = object_or_func
    if hasattr(object_or_func, '__call__'):
        obj = object_or_func()

    if isinstance(obj, types.ModuleType):
        dct = {}
        for k in dir(obj):
            if k.startswith("__"):
                continue
            dct[k] = getattr(obj, k)

        obj = dct

    return obj


def extend_module_from_entry_point(module_name, ns):
    """
    Extend a settings module from entry_point hooks
    """
    for e in get_entry_points(ns, 'default_settings'):
        extend_module(module_name, entry_point_to_object(e))


def extend_dict_from_entry_point(settings_object, ns, entry_point_name):
    for e in get_entry_points(ns, entry_point_name):
        settings_object.update(entry_point_to_object(e))

    return settings_object


def extend_list_from_entry_point(settings_object, ns, entry_point_name,
                                 unique=True):
    settings_object = list(settings_object)
    for e in get_entry_points(ns, entry_point_name):
        obj = entry_point_to_object(e)
        for row in obj:
            # skip duplicate entries
            if row in settings_object:
                continue

            if type(row) == dict and (row.get('before', False) or
                                      row.get('after', False)):

                insert_at = len(settings_object)
                if row.get('before', False):
                    try:
                        position = settings_object.index(row.get('before'))
                        insert_at = position - 1
                    except ValueError:
                        pass
                else:
                    try:
                        position = settings_object.index(row.get('after'))
                        insert_at = position + 1
                    except ValueError:
                        pass

                if insert_at < 0:
                    insert_at = 0

                inserts = row.get('insert', [])
                if not type(inserts) == list:
                    inserts = [inserts]

                for entry in inserts:
                    if not entry in settings_object:
                        settings_object.insert(insert_at, entry)
                        insert_at = insert_at + 1
            else:
                settings_object.append(row)

    return settings_object


def collect_defaults(ns):
    settings = defaultdict(lambda: [])
    for e in get_entry_points('synnefo', 'default_settings'):
        attrs = dir(e.load())
        settings[e.dist.key] = settings[e.dist.key] + attrs

    return settings


def extend_settings(mname, ns):
    extend_module_from_entry_point(mname, ns)


def extend_urls(patterns, ns):
    for e in get_entry_points(ns, 'urls'):
        patterns += e.load()

    return patterns
