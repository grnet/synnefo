# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed

from synnefo.lib.dictconfig import dictConfig

import logging


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


class LoggingConfigMiddleware:
    def __init__(self):
        """Initialise the logging setup from settings.

        Logging setup is initialized only in the first request.
        """
        logging_setting = getattr(settings, 'LOGGING_SETUP', None)
        if logging_setting:
            # Disable handlers that are not used by any logger.
            active_handlers = set()
            loggers = logging_setting.get('loggers', {})
            for logger in loggers.values():
                active_handlers.update(logger.get('handlers', []))
            handlers = logging_setting.get('handlers', {})
            for handler in handlers:
                if handler not in active_handlers:
                    handlers[handler] = {'class': 'logging.NullHandler'}

            logging.NullHandler = NullHandler
            dictConfig(logging_setting)
        raise MiddlewareNotUsed('Logging setup only.')
