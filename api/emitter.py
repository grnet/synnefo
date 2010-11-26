# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

from piston.resource import Resource as BaseResource
import re

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

# XXX: works as intended but not used since piston's XMLEmitter doesn't output
# XML according to our spec :(
class Resource(BaseResource):
    def determine_emitter(self, request, *args, **kwargs):
        """
        Override default emitter policy to account for Accept header

        emitter_format (.json or .xml suffix in URL) always takes precedence.

        After that, the Accept header is checked; if both JSON and XML are
        equally preferred, use JSON.

        If none of the two were provided, then use JSON as per the
        specification.
        """

        em = request.GET.get('format', 'xml')
        if 'emitter_format' in kwargs:
            em = kwargs.pop('emitter_format')
        elif 'HTTP_ACCEPT' in request.META:
            accepts = parse_accept_header(request.META['HTTP_ACCEPT'])
            for content_type, quality in accepts:
                if content_type == 'application/json':
                    break
                elif content_type == 'application/xml':
                    em = request.GET.get('format', 'xml')
                    break

        return em
