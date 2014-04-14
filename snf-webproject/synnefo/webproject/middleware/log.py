# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
