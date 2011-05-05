from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed

import logging
import logging.handlers
import logging.config

__all__ = ('LoggingConfigMiddleware',)

class LoggingConfigMiddleware:
    def __init__(self):
        '''Initialise the logging setup from settings, called on first request.'''
        if getattr(settings, 'DEBUG', False):
            logging.basicConfig(level = logging.DEBUG, format = '%(asctime)s [%(levelname)s] %(name)s %(message)s', datefmt = '%Y-%m-%d %H:%M:%S')
        else:
            logging.basicConfig(level = logging.INFO, format = '%(asctime)s [%(levelname)s] %(name)s %(message)s', datefmt = '%Y-%m-%d %H:%M:%S')
        raise MiddlewareNotUsed('Logging setup only.')
