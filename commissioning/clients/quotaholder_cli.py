#!/usr/bin/env python
from commissioning.clients.kamaki_cli import cli_generator
from commissioning.clients.quotaholder_plugin import quotaholder_plugin

class quotaholder_cli(cli_generator):
    def __init__(self):
        self.plugin = quotaholder_plugin
        self.api_spec = self.plugin.api_spec
        self.appname = self.plugin.appname
