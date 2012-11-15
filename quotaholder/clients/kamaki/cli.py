#!/usr/bin/env python
from commissioning.lib.kamaki import cli_generator
from . import quotaholder_plugin

class quotaholder_cli(cli_generator):

    def __init__(self):
        self.plugin = quotaholder_plugin
        self.add_context = True
        super(self.__class__, self).__init__()
