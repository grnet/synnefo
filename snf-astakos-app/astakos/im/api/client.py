#!/usr/bin/env python
from commissioning.clients.http import main, HTTP_API_Client
from astakos.im.api.spec import AstakosAPI


class AstakosHTTP(HTTP_API_Client):
    api_spec = AstakosAPI()


if __name__ == '__main__':
    main(callpoint=AstakosHTTP())
