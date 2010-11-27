# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

from piston.resource import Resource as BaseResource
from synnefo.helpers import parse_accept_header
import synnefo.api.emitter # load our own Emitter

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

        em = request.GET.get('format', 'json')
        if 'emitter_format' in kwargs and \
           kwargs["emitter_format"] is not None:
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

