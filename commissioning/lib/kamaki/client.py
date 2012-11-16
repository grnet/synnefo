#!/usr/bin/env python

from commissioning import Callpoint, CallError
from commissioning.utils.debug import debug
from kamaki.clients import Client

from json import loads as json_loads, dumps as json_dumps

class Kamaki_plugin(Callpoint):

    def __init__(self, base_url, token):
        super(Kamaki_plugin, self).__init__()
        self._kc = Client(base_url, token)

    def do_make_call(self, api_call, data):

        _kc = self._kc
        
        gettable = ['list', 'get', 'read']
        method = (_kc.get if any(api_call.startswith(x) for x in gettable)
                  else _kc.post)

        path = api_call
        json_data = json_dumps(data)
        debug("%s %s\n%s\n<<<\n", method.func_name, path, json_data)
        
        resp = method(path, data=json_data, success=(200,450,500))
        debug(">>>\nStatus: %s", resp.status_code)
        
        body = resp.text
        debug("\n%s\n<<<\n", body[:128] if body else None)

        status = int(resp.status_code)
        if status == 200:
            return json_loads(body)
        else:
            try:
                error = json_loads(body)
            except ValueError, e:
                exc = CallError(body, call_error='ValueError')
            else:
                exc = CallError.from_dict(error)
            raise exc
