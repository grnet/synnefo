# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

import re
from django.conf.urls.defaults import url

_accept_re = re.compile(r'([^\s;,]+)(?:[^,]*?;\s*q=(\d*(?:\.\d+)?))?')


def parse_accept_header(value):
    """Parse an HTTP Accept header

    Returns an ordered by quality list of tuples (value, quality)
    """
    if not value:
        return []

    result = []
    for match in _accept_re.finditer(value):
        quality = match.group(2)
        if not quality:
            quality = 1
        else:
            quality = max(min(float(quality), 1), 0)
        result.append((match.group(1), quality))

    # sort by quality
    result.sort(key=lambda x: x[1])

    return result


def url_with_format(regex, *args, **kwargs):
    """
    An extended url() that adds an .json/.xml suffix to the end to avoid DRY
    """
    if regex[-1] == '$' and regex[-2] != '\\':
        regex = regex[:-1]
    regex = regex + r'(\.(?P<emitter_format>json|xml))?$'
    return url(regex, *args, **kwargs)
