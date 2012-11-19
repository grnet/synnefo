#!/usr/bin/env python

from quotaholder.api import QuotaholderAPI
from commissioning.lib.kamaki import kamaki_client

class quotaholder_client(kamaki_client):

    api_spec = QuotaholderAPI()
    appname = 'quotaholder'

    def __init__(self, base_url=None, token=None):
        default_url = 'http://127.0.0.1:8008/api/quotaholder/v'
        base_url = base_url if base_url else default_url
        super(self.__class__, self).__init__(base_url, token)
