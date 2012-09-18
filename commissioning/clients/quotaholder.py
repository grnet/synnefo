#!/usr/bin/env python
from commissioning.clients.http import main, HTTP_API_Client
from commissioning import QuotaholderAPI


class QuotaholderHTTP(HTTP_API_Client):
    api_spec = QuotaholderAPI()

