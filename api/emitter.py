# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

import re
from xml.dom import minidom
from django.conf.urls.defaults import url
from piston.emitters import Emitter, Mimer
from piston.resource import Resource as BaseResource

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

class OSXMLEmitter(Emitter):
    """
    Custom XML Emitter that handles some special stuff needed by the API.

    Shamelessly stolen^Wborrowed code (sans Piston integration) by OpenStack's
    Nova project and hence:

    Copyright 2010 United States Government as represented by the
    Administrator of the National Aeronautics and Space Administration.
    Copyright 2010 OpenStack LLC.

    and licensed under the Apache License, Version 2.0
    """

    _metadata = {
            "server": [ "id", "imageId", "name", "flavorId", "hostId",
                        "status", "progress", "progress" ],
            "flavor": [ "id", "name", "ram", "disk" ],
            "image": [ "id", "name", "updated", "created", "status",
                       "serverId", "progress" ],
        }

    def _to_xml_node(self, doc, nodename, data):
        """Recursive method to convert data members to XML nodes."""
        result = doc.createElement(nodename)
        if type(data) is list:
            if nodename.endswith('s'):
                singular = nodename[:-1]
            else:
                singular = 'item'
            for item in data:
                node = self._to_xml_node(doc, singular, item)
                result.appendChild(node)
        elif type(data) is dict:
            attrs = self._metadata.get(nodename, {})
            for k, v in data.items():
                if k in attrs:
                    result.setAttribute(k, str(v))
                else:
                    node = self._to_xml_node(doc, k, v)
                    result.appendChild(node)
        else: # atom
            node = doc.createTextNode(str(data))
            result.appendChild(node)
        return result

    def render(self, request):
        data = self.construct()
        # We expect data to contain a single key which is the XML root.
        root_key = data.keys()[0]
        doc = minidom.Document()
        node = self._to_xml_node(doc, root_key, data[root_key])
        return node.toprettyxml(indent='    ')

Emitter.register('xml', OSXMLEmitter, 'application/xml')
Mimer.register(lambda *a: None, ('application/xml',))

def url_with_format(regex, *args, **kwargs):
    """
    An extended url() that adds an .json/.xml suffix to the end to avoid DRY
    """
    if regex[-1] == '$' and regex[-2] != '\\':
        regex = regex[:-1]
    regex = regex + r'(\.(?P<emitter_format>json|xml))?$'
    return url(regex, *args, **kwargs)
