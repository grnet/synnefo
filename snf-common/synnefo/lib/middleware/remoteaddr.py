class RemoteAddrMiddleware(object):
    """
    A generic middleware that sets the REMOTE_ADDR if not sent by the server.

    Solves issues with nginx deployment that don't sets the REMOTE_ADDR meta
    key.
    """
    def process_request(self, request):
        if 'REMOTE_ADDR' in request.META:
            request.META['REMOTE_ADDR'] = request.META.get('HTTP_X_REAL_IP',
                                                           None)
