#!/usr/bin/env python

from httplib import HTTPConnection, HTTPException
from urlparse import urlparse
from commissioning import Callpoint
from commissioning.utils.clijson import clijson

import logging

from json import loads as json_loads, dumps as json_dumps


def init_logger_file(name, level='DEBUG'):
    logger = logging.getLogger(name)
    handler = logging.FileHandler(name + '.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    level = getattr(logging, level, logging.DEBUG)
    logger.setLevel(level)
    return logger

def init_logger_stdout(name, level='DEBUG'):
    logger = logging.getLogger(name)
    from sys import stdout
    handler = logging.StreamHandler(stdout)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    level = getattr(logging, level, logging.DEBUG)
    logger.setLevel(level)
    return logger


class quota_holder_allocation(object):
    client = None
    serial = None

    def __init__(self, *allocations, **pre_allocations):
        allocations = canonify_list_of_allocations(allocations)
        pre_allocations = pre_allocations.items()
        pre_allocations = [(name, pre, 0) for name, pre in pre_allocations]
        pre_allocations = canonify_list_of_allocations(pre_allocations)
        allocations.extend(pre_allocations)
        self.allocations = allocations

        if self.client is None:
            self.client = QuotaholderClient.instance()

    def __call__(self, func):
        def wrapped(*args, **kw):
            client = self.client
            serial = client.get_provision(self.allocations)
            try:
                ret = func(*args, **kw)
            except Exception:
                client.recall_provision(serial)
                raise
            else:
                client.commit_provision(serial)

            return ret

        return wrapped

    def __enter__(self):
        self.serial = self.client.get_provision(self.allocations)

    def __exit__(self, exctype, exc, traceback):
        serial = self.serial
        client = self.client

        if exctype is None:
            client.commit_provision(serial)
        else:
            client.recall_provision(serial)
            raise


class GenericHTTPClient(Callpoint):
    """Synchronous http client for quota holder API"""

    appname = 'http'
    _http_client = None
    quota_holder_allocation = quota_holder_allocation

    def init_connection(self, connection):
        self.url = connection

        class quota_holder_allocator_class(quota_holder_allocation):
            client = self

        self.quota_holder_allocation = quota_holder_allocator_class
        self.logger = logging.getLogger(self.appname)

    @classmethod
    def instance(cls):
        client = cls._http_client
        if client is None:
            url = "http://127.0.0.1:8000/%s/%s" % (cls.appname, cls.version)
            client = cls(url)
            self._http_client = client

        return client

    def commit(self):
        return

    def rollback(self):
        return

    def debug(self, fmt, *args):
        self.logger.debug(fmt % args)

    def do_make_call(self, api_call, data):
        url = urlparse(self.url)
        scheme = url.scheme
	Connection = HTTPConnection
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
        else:
            raise ValueError("Unsupported scheme %s" % (scheme,))

        path = url.path.strip('/')
        path = ('/' + path + '/' + api_call) if path else ('/' + api_call)

        netloc = url.netloc.rsplit(':', 1)
        netloclen = len(netloc)
        if netloclen == 1:
            host = netloc[0]
        elif netloclen == 2:
            host, port = netloc
        else:
            msg = "Unsupported network location type '%s'" % (netloc,)
            raise ValueError(msg)

        self.debug("Connecting to %s:%s\n>>>", host, port)
        conn = Connection(host, port)

        if (api_call.startswith('list') or
            api_call.startswith('get') or
            api_call.startswith('read')):

                method = 'GET'
        else:
                method = 'POST'

        json_data = self.json_dumps(data)
        self.debug("%s %s\n%s\n<<<\n", method, path, json_data)

        req = conn.request(method, path, body=json_data)
        resp = conn.getresponse()
        self.debug(">>>\nStatus: %s", resp.status)

        for name, value in resp.getheaders():
            self.debug("%s: %s", name, value)

        body = ''
        while 1:
            s = resp.read() 
            if not s:
                break
            body += s

        self.debug("\n%s\n<<<\n", body)

        status = int(resp.status)
        if status == 200:
            if body:
                body = json_loads(body)
            return body
        else:
            return body

        raise IOError("Call Failed", str(resp.status))

API_Callpoint = GenericHTTPClient


def main():
    from sys import argv, stdout
    from os.path import basename, expanduser
    from time import time
    from commissioning import get_callpoint

    progname = basename(argv[0])
    if progname == 'http.py':
        if len(argv) < 2:
            usage = "./http.py <appname> <app args...>"
            print(usage)
            raise SystemExit

        argv = argv[1:]
        progname = basename(argv[0])

    init_logger_stdout(progname)

    pointname = 'clients.' + progname
    API_Callpoint = get_callpoint(pointname, automake='http')
    api = API_Callpoint.api_spec

    usage = "API Calls:\n\n"

    for call_name in sorted(api.call_names()):
        canonical = api.input_canonical(call_name)
        argstring = canonical.tostring(multiline=1, showopts=0)
        usage += call_name + '.' + argstring + '\n\n'

    import argparse
    parser = argparse.ArgumentParser    (
            formatter_class =   argparse.RawDescriptionHelpFormatter,
            description     =   "%s http client" % (progname,),
            epilog          =   usage,
    )

    urlhelp = 'set %s server base url' % (progname,)
    parser.add_argument('--url', type=str, dest='url',
                        action='store', help=urlhelp)

    jsonhelp = 'intepret data as json'
    parser.add_argument('--json', dest='json_data', action='store_false',
                        default=True, help=jsonhelp)

    callhelp = 'api call to perform'
    parser.add_argument('api_call', type=str, action='store', nargs=1,
                        help=callhelp)

    arghelp = 'data to provide to api call'
    parser.add_argument('data', type=str, action='store', nargs='*',
                        help=callhelp)

    urlfilepath = expanduser('~/.qholderrc')

    def get_url():
        try:
            with open(urlfilepath) as f:
                url = f.read()
        except Exception:
            m = "Cannot load url from %s. Try --url." % (urlfilepath,)
            raise ValueError(m)
        return url

    def set_url(url):
        url = url.strip('/')
        with open(urlfilepath, "w") as f:
            f.write(url)
        print "Base URL set to '%s'" % (url,)

    args = parser.parse_args(argv[1:])

    api_call = args.api_call[0]
    api.input_canonical(api_call)

    if args.url:
        set_url(args.url)

    url = get_url()

    data = args.data
    if data:
        if data[0] == '-':
            from sys import stdin
            data = stdin.read()
        else:
            data = clijson(data)

    if not data:
        data = None

    client = API_Callpoint(url)
    print "data", data
    print(client.make_call_from_json(api_call, data))


if __name__ == '__main__':
    main()

