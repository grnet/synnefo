# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

import re

_strip_url_re = re.compile(r'^https?://[^/]+')

class StripURLMiddleware(object):
    """
    At least some Cloud Servers API clients tend to use full URLs as request
    paths, contrary to all RFCs.

    This is a) wrong, b) incompatible with Django's urlconf.

    This middleware attempts to strip such URLs so that the URL dispatcher can
    process it normally.

    It should be inserted as early as possible in MIDDLEWARE_CLASSES
    """

    def process_request(self, request):
        request.path = re.sub(_strip_url_re, '', request.path)
        request.path_info = re.sub(_strip_url_re, '', request.path_info)
