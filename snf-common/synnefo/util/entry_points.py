# Copyright 2011 GRNET S.A. All rights reserved.
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
                if row.get('before', False):
                    position = settings_object.index(row.get('before'))
                    insert_at = position - 1
                else:
                    position = settings_object.index(row.get('after'))
                    insert_at = position + 1

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
