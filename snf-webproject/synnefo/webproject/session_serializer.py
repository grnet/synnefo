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
import datetime
from dateutil import parser
from django.core.serializers.json import DjangoJSONEncoder

TYPE_TOKEN = '_type'
VALUE_TOKEN = '_value'
DATE_TYPE_TOKEN = 'date'

logger = logging.getLogger(__name__)


class DateTimeDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook,
                                  *args, **kwargs)

    def object_hook(self, obj):
        if set(obj.keys()) != set([TYPE_TOKEN, VALUE_TOKEN]):
            return obj

        typ = obj[TYPE_TOKEN]
        val = obj[VALUE_TOKEN]
        if typ == DATE_TYPE_TOKEN:
            try:
                r = parser.parse(val)
            except Exception as e:
                logger.error("Could not deserialize date from: %s", str(val))
                logger.exception(e)
                return obj

            logger.debug("Deserialized date str '%s' to %s", val, repr(r))
            return r

        raise ValueError("Unrecognized type %s" % typ)


class DateTimeAwareJSON(object):
    def dumps(self, obj):
        return json.dumps(obj, cls=DateJSONEncoder)

    def loads(self, data):
        try:
            return json.loads(data, cls=DateTimeDecoder)
        except Exception as e:
            logger.error("Failed to load session: " + str(e))
            raise


class DateJSONEncoder(DjangoJSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time and add type
    information.
    """

    def default(self, o):
        """
        Serialize a date object similar to Django's Json Encoder, but add a
        type field for deterministic deserialization.
        """
        r = super(DateJSONEncoder, self).default(o)
        datetime_classes = (datetime.datetime, datetime.date, datetime.time)
        if isinstance(o, datetime_classes):
            logger.debug("Converted date type %s to '%s'", repr(o), r)
            return {TYPE_TOKEN: DATE_TYPE_TOKEN, VALUE_TOKEN: r}

        return r
