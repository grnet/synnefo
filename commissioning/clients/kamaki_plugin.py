#!/usr/bin/env python

from synnefo.lib.pool.http import get_http_connection
from urlparse import urlparse
from commissioning import Callpoint, CallError
from commissioning.utils.clijson import clijson
from commissioning import QuotaholderAPI

from kamaki.clients import Client

import logging

from json import loads as json_loads, dumps as json_dumps

_logger = None

def init_logger_file(name, level='DEBUG'):
    logger = logging.getLogger(name)
    handler = logging.FileHandler(name + '.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    level = getattr(logging, level, logging.DEBUG)
    logger.setLevel(level)
    global _logger
    _logger = logger
    return logger

def init_logger_stderr(name, level='DEBUG'):
    logger = logging.getLogger(name)
    from sys import stderr
    handler = logging.StreamHandler(stderr)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    level = getattr(logging, level, logging.DEBUG)
    logger.setLevel(level)
    global _logger
    _logger = logger
    return logger


def debug(fmt, *args):
    global _logger
    if _logger is None:
        init_logger_stderr('logger')
        _logger.setLevel(logging.DEBUG)
    _logger.debug(fmt % args)

# def debug(fmt, *args):
#     pass


class Kamaki_plugin(Callpoint):

    appname = 'kamaki_plugin'

    def __init__(self, base_url, token):
        super(Kamaki_plugin, self).__init__()
        self._kc = Client(base_url, token)
                

    def init_connection(self, connection):
        self.url = connection

    def commit(self):
        return

    def rollback(self):
        return

    def do_make_call(self, api_call, data):

        _kc = self._kc
        
        gettable = ['list', 'get', 'read']
        method = _kc.get if any(api_call.startswith(x)
                                for x in gettable) else _kc.post

        path = '/api/quotaholder/v/' + api_call
        json_data = self.json_dumps(data)
        debug("%s %s\n%s\n<<<\n", method, path, json_data)
        
        resp = method(path, data=json_data)
        debug(">>>\nStatus: %s", resp.status_code)
        
        # for name, value in resp.getheaders():
        #     debug("%s: %s", name, value)

        status = int(resp.status_code)
        if status == 200:
            body = resp.json
            debug("\n%s\n<<<\n", body[:128])
            return body
        else:
            try:
                error = resp.json()
            except ValueError, e:
                exc = CallError(body, call_error='ValueError')
            else:
                exc = CallError.from_dict(error)
            raise exc

    def call(self, method, arglist):
        argdict = self.api_spec.input_canonicals[method].parse(arglist)
        f = getattr(self, method)
        return f(**argdict)

class QHKamaki(Kamaki_plugin):
    api_spec = QuotaholderAPI()
    def __init__(self, base_url='http://127.0.0.1:8000', token=''):
        super(QHKamaki, self).__init__(base_url, token)

