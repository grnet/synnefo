#!/usr/bin/env python

from synnefo.lib.pool.http import get_http_connection
from urlparse import urlparse
from commissioning import Callpoint, CallError
from commissioning.utils.clijson import clijson
from commissioning.utils.debug import debug

from json import loads as json_loads, dumps as json_dumps

class HTTP_API_Client(Callpoint):
    """Synchronous http client for quota holder API"""

    appname = 'http'

    def init_connection(self, connection):
        self.url = connection

    def commit(self):
        return

    def rollback(self):
        return

    def do_make_call(self, api_call, data):
        url = urlparse(self.url)
        scheme = url.scheme
        path = url.path.strip('/')
        path = ('/' + path + '/' + api_call) if path else ('/' + api_call)
        netloc = url.netloc

        conn = None
        try:
            debug("Connecting to %s\n>>>", netloc)
            conn = get_http_connection(netloc=netloc, scheme=scheme)
            if (api_call.startswith('list') or
                api_call.startswith('get') or
                api_call.startswith('read')):

                    method = 'GET'
            else:
                    method = 'POST'

            json_data = self.json_dumps(data)
            debug("%s %s\n%s\n<<<\n", method, path, json_data)

            req = conn.request(method, path, body=json_data)
            resp = conn.getresponse()
            debug(">>>\nStatus: %s", resp.status)

            for name, value in resp.getheaders():
                debug("%s: %s", name, value)

            body = ''
            while 1:
                s = resp.read() 
                if not s:
                    break
                body += s

            debug("\n%s\n<<<\n", body[:128])

            status = int(resp.status)
            if status == 200:
                if body:
                    body = json_loads(body)
                return body
            else:
                try:
                    error = json_loads(body)
                except ValueError, e:
                    exc = CallError(body, call_error='ValueError')
                else:
                    exc = CallError.from_dict(error)
                raise exc
        finally:
            if conn is not None:
                conn.close()

API_Callpoint = HTTP_API_Client


def main():
    from sys import argv, stdout
    from os.path import basename, expanduser
    from time import time
    from commissioning import get_callpoint
    from commissioning.utils.debug import init_logger_stderr

    progname = basename(argv[0])
    h, s, t = progname.rpartition('.')
    if t == 'py':
        progname = h

    if progname == 'http':
        if len(argv) < 2:
            usage = "./http <appname> <app args...>"
            print(usage)
            raise SystemExit

        argv = argv[1:]
        progname = basename(argv[0])

    init_logger_stderr(progname)

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

    urlfilepath = expanduser('~/.%s.urlrc' % progname)

    def get_url():
        try:
            with open(urlfilepath) as f:
                url = f.read().strip()
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

    if args.url:
        set_url(args.url)

    api_call = args.api_call[0]
    api.input_canonical(api_call)

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
    print(client.make_call_from_json(api_call, data))


if __name__ == '__main__':
    main()

