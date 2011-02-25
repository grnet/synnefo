# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

from xml.dom import minidom
from piston.emitters import Emitter, Mimer

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
            'ip': ['addr'],
            'ip6': ['addr'],
            'meta': ['key'],
            "flavor": [ "id", "name", "ram", "disk", "cpu" ],
            "image": [ "id", "name", "updated", "created", "status",
                       "serverId", "progress", "size", "description"],
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
