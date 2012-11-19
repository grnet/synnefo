#!/usr/bin/env python
from commissioning.lib.kamaki import kamaki_cli
from . import quotaholder_client

class quotaholder_cli(kamaki_cli):

    def __init__(self):
        self.client = quotaholder_client
        self.add_context = True
        self.description = 'Quotaholder description'
        super(self.__class__, self).__init__()
