#!/usr/bin/env python
from commissioning import Callpoint
from commissioning.clients.http import main, HTTP_API_Client
from commissioning.specs.fscrud import API_Spec as FSCRUD_API


class FSCRUD_HTTP(HTTP_API_Client):
    api_spec = FSCRUD_API()


class FSCRUD_Debug(Callpoint):
    api_spec = FSCRUD_API()

    def init_connection(self, connection):
        self.connection = connection
        print 'connecting to', connection

    def commit(self):
        pass

    def abort(self):
        pass

    def do_make_call(self, call_name, call_data):
        print call_name, str(call_data)


if __name__ == '__main__':
    main()

