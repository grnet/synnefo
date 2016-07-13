# Copyright (C) 2010-2016 GRNET S.A.
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

import copy
import json
from django.http import HttpRequest, QueryDict

CLEANSED_SUBSTITUTE = u'********************'


def cleanse(kvs, hidden, subst=CLEANSED_SUBSTITUTE, case=True):
    """
    Substitute values of keys found in hidden list.
    Try to recursively clean dictionaries found in keys and values of the given
    'kvs' argument.

    :param kvs: dictionary to cleanse
    :param hidden: list of keywords to search for
    :param subst: text to substitute with when a given keyword is found
    :param case: flag to compare case sensitive
    """

    if hidden == '__ALL__':
        for key in kvs.keys():
            if isinstance(key, dict):
                key = cleanse(key, hidden, subst, case)
            kvs[key] = subst

        return kvs

    for key in kvs.keys():
        cleansed_key = key
        if isinstance(key, dict):
            cleansed_key = cleanse(key, hidden, subst, case)

        for h in hidden:
            replace = False
            if not case and isinstance(key, basestring):
                cmp_key = key.lower()
                cmp_h = h.lower()
            else:
                cmp_key = key
                cmp_h = h

            if cmp_h in cmp_key:
                replace = True
                break

        v = kvs[key]
        del kvs[key]

        if replace:
            kvs[cleansed_key] = subst
        elif isinstance(v, dict):
            kvs[cleansed_key] = cleanse(v, hidden, subst, case)
        else:
            kvs[cleansed_key] = v

    return kvs


def cleanse_str(s, hidden, subst=CLEANSED_SUBSTITUTE, case=True, reason=None):
    """
    Take a string and cleanse it if it contains any of the hidden values
    """
    s_cmp = s
    if not case:
        s_cmp = s.lower()

    for h in hidden:
        h_cmp = h
        if not case:
            h_cmp = h.lower()

        if h_cmp in s_cmp:
            if reason is not None:
                return "%s (reason: %s)" % (subst, reason)
            return subst

    return s


def cleanse_jsonstr(s, hidden, subst=CLEANSED_SUBSTITUTE, case=True):
    """
    Take a string that is supposed to be a json string convert it to dictionary
    and cleanse it recursively. If it cannot be converted to dictionary,
    it is cleansed as a plain string.
    """

    try:
        json_data = json.loads(s)
        cleansed_json = cleanse(json_data, hidden, case=case)
        return json.dumps(cleansed_json)
    except:
        return cleanse_str(s, hidden, subst, case,
                           reason="Cannot cleanse it as a json string")


def cleanse_formstr(s, hidden, subst=CLEANSED_SUBSTITUTE, case=True):
    """
    Take a string and cleanse it as if it is a
    'application/x-www-form-urlencoded' string. If it cannot be converted to
    django's QueryDict, it is cleansed as a plain string.
    """

    try:
        form_data = QueryDict(s, mutable=True)
        cleansed_form = cleanse(form_data, hidden, case=case)
        return cleansed_form.urlencode()
    except:
        return cleanse_str(s, hidden, subst, case,
                           reason="Cannot cleanse it as post parameters string")


def cleanse_request(req, hidden_cookies, hidden):
    """
    Return a cleansed copy of an HttpRequest instance.
    """

    if not isinstance(req, HttpRequest):
        return req

    req_copy = copy.copy(req)

    if req.method == 'GET':
        get = getattr(req, 'GET').copy()
        setattr(req_copy, 'GET', cleanse(get, hidden, case=False))
    else:
        post = getattr(req, 'POST')
        if post and len(post) > 0:
            meta = getattr(req, 'META')
            content_type =  meta.get('CONTENT_TYPE', None)
            if content_type is None:
                subst = CLEANSED_SUBSTITUTE
                reason = "Could not find content type"
                cleansed_post = QueryDict("%s (reason: %s)" % (subst, reason))
            elif content_type.lower() == 'application/json':
                # this should contain just one key
                cleansed_post = QueryDict("", mutable=True)
                for key in post.keys():
                    cleansed_json = cleanse_jsonstr(key, hidden, case=False)
                    cleansed_post[cleansed_json] = post[key]
            elif content_type.lower() == 'application/x-www-form-urlencoded':
                post = getattr(req, 'POST').copy()
                cleansed_post = cleanse(post, hidden, case=False)
            else:
                subst = CLEANSED_SUBSTITUTE
                reason = "Unhandled content type '%s'" % content_type
                cleansed_post = QueryDict("%s (reason: %s)" % (subst, reason))
        else:
            cleansed_post = post
        setattr(req_copy, 'POST', cleansed_post)

    cookies = getattr(req, 'COOKIES').copy()
    setattr(req_copy, 'COOKIES', cleanse(cookies, hidden_cookies, case=False))
    meta = getattr(req, 'META').copy()
    setattr(req_copy, 'META', cleanse(meta, hidden, case=False))

    return req_copy
