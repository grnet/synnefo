from django.core.serializers.json import DjangoJSONEncoder
import json


class DateTimeAwareJSON(object):
    def dumps(self, obj):
        return json.dumps(obj, cls=DjangoJSONEncoder)

    def loads(self, data):
        return json.loads(data)
