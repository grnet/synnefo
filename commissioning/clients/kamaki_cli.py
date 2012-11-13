#!/usr/bin/env python

from commissioning.utils.betteron import betteron_decode
from kamaki.cli.commands import _command_init
from kamaki.cli import command

class cli_generator():
    api_spec = None
    appname = None
    plugin = None

    def get_doc(self, method):
        return self.api_spec.doc_strings[method]

    def parse(self, method, arglist):
        a, rest = betteron_decode(arglist)
        a = [(None, None)] + a
        argdict = self.api_spec.input_canonicals[method].parse(a)
        return argdict

    def generate_all(self):
        for f in self.api_spec.call_names():
            c = self.mkClass(f)
            command()(c)

    def mkClass(self, method):
        class C(_command_init):
            __doc__ = self.get_doc(method)
            def init(this):
                this.base_url = (this.config.get(self.appname, 'url') or
                                 this.config.get('global', 'url'))
                this.client = (self.plugin(this.base_url)
                               if this.base_url else self.plugin())

            def call(this, method, args):
                arglist = '[' + ' '.join(args) + ']'
                argdict = self.parse(method, arglist)
                f = getattr(this.client, method)
                return f(**argdict)

            def main(this, *args):
                this.init()
                r = this.call(method, args)
                print r

        C.__name__ = self.appname + '_' + method
        return C
