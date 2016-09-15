# Copyright (C) 2010-2016 GRNET S.A. and individual contributors
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

import logging


class Suppress(logging.Filter):
    def __init__(self, keywords=None):
        if keywords is None:
            keywords = []

        self.keywords = keywords

    def filter(self, record):
        # Return false to suppress message.
        return not any([warn in record.getMessage() for warn in self.keywords])


class SuppressDeprecated(Suppress):
    WARNINGS_TO_SUPPRESS = [
        'RemovedInDjango18Warning',
    ]

    def __init__(self):
        super(SuppressDeprecated, self).\
                __init__(keywords=self.WARNINGS_TO_SUPPRESS)
