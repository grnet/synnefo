# Copyright (C) 2010-2016 GRNET S.A.
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

import json
import logging
from dateutil import parser
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger(__name__)


class DateTimeDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook,
                                  *args, **kwargs)

    def object_hook(self, obj):
        for (key, value) in obj.items():
            try:
                # Convert only top level strings, since there are no nested
                # dates in the Session object. In such a case, this must be
                # extended to recursively convert isoformatted strings to
                # datetime objects.
                obj[key] = parser.parse(value)
            except Exception:
                pass
        return obj


class DateTimeAwareJSON(object):
    def dumps(self, obj):
        return json.dumps(obj, cls=DjangoJSONEncoder)

    def loads(self, data):
        try:
            return json.loads(data, cls=DateTimeDecoder)
        except Exception as e:
            logger.error("Failed to load session: " + str(e))
            raise
