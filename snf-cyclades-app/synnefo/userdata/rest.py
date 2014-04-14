#
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

import logging

from django import http
from django.utils import simplejson as json
from django.core.urlresolvers import reverse
from django.http import HttpResponse

from django.core.exceptions import ValidationError, NON_FIELD_ERRORS

from snf_django.lib.astakos import get_user
from django.conf import settings


class View(object):
    """
    Intentionally simple parent class for all views. Only implements
    dispatch-by-method and simple sanity checking.
    """

    method_names = ['GET', 'POST', 'DELETE', 'HEAD', 'OPTIONS', 'TRACE']

    def __init__(self, *args, **kwargs):
        """
        Constructor. Called in the URLconf; can contain helpful extra
        keyword arguments, and other things.
        """
        self.logger = logging.getLogger(self.model._meta.db_table)
        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in kwargs.items():
            if key in self.method_names:
                raise TypeError(u"You tried to pass in the %s method name as a"
                                u" keyword argument to %s(). Don't do that."
                                % (key, self.__class__.__name__))
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise TypeError(u"%s() received an invalid keyword %r" % (
                    self.__class__.__name__,
                    key,
                ))

    @classmethod
    def as_view(cls, *initargs, **initkwargs):
        """
        Main entry point for a request-response process.
        """
        def view(request, *args, **kwargs):
            get_user(request, settings.ASTAKOS_AUTH_URL)
            if not request.user_uniq:
                return HttpResponse(status=401)
            self = cls(*initargs, **initkwargs)
            return self.dispatch(request, *args, **kwargs)
        return view

    def dispatch(self, request, *args, **kwargs):
        # Try to dispatch to the right method for that; if it doesn't exist,
        # raise a big error.
        if hasattr(self, request.method.upper()):
            self.request = request
            self.args = args
            self.kwargs = kwargs
            data = request.body

            if request.method.upper() in ['POST', 'PUT']:
                # Expect json data
                if request.META.get('CONTENT_TYPE').startswith(
                        'application/json'):
                    try:
                        data = json.loads(data)
                    except ValueError:
                        return \
                            http.HttpResponseServerError('Invalid JSON data.')
                else:
                    return http.HttpResponseServerError(
                        'Unsupported Content-Type.')
            try:
                return getattr(self, request.method.upper())(
                    request, data, *args, **kwargs)
            except ValidationError, e:
                # specific response for validation errors
                return http.HttpResponse(
                    json.dumps({'errors': e.message_dict,
                                'non_field_key': NON_FIELD_ERRORS}),
                status=422, content_type="application/json")

        else:
            allowed_methods = \
                [m for m in self.method_names if hasattr(self, m)]
            return http.HttpResponseNotAllowed(allowed_methods)


class JSONRestView(View):
    """
    Class that provides helpers to produce a json response
    """

    url_name = None

    def __init__(self, url_name, *args, **kwargs):
        self.url_name = url_name
        return super(JSONRestView, self).__init__(*args, **kwargs)

    def update_instance(self, i, data, exclude_fields=[]):
        update_keys = data.keys()
        for field in i._meta.get_all_field_names():
            if field in update_keys and (field not in exclude_fields):
                i.__setattr__(field, data[field])

        return i

    def instance_to_dict(self, i, exclude_fields=[]):
        """
        Convert model instance to python dict
        """
        d = {}
        d['uri'] = reverse(self.url_name, kwargs={'id': i.pk})

        for field in i._meta.get_all_field_names():
            if field in exclude_fields:
                continue

            d[field] = i.__getattribute__(field)
        return d

    def qs_to_dict_iter(self, qs, exclude_fields=[]):
        """
        Convert queryset to an iterator of model instances dicts
        """
        for i in qs:
            yield self.instance_to_dict(i, exclude_fields)

    def json_response(self, data):
        return http.HttpResponse(json.dumps(data), mimetype="application/json")


class ResourceView(JSONRestView):
    method_names = ['GET', 'POST', 'PUT', 'DELETE']

    model = None
    exclude_fields = []

    def queryset(self):
        return self.model.objects.all()

    def instance(self):
        """
        Retrieve selected instance based on url parameter

        id parameter should be set in urlpatterns expression
        """
        try:
            return self.queryset().get(pk=self.kwargs.get("id"))
        except self.model.DoesNotExist:
            raise http.Http404

    def GET(self, request, data, *args, **kwargs):
        return self.json_response(
            self.instance_to_dict(self.instance(), self.exclude_fields))

    def PUT(self, request, data, *args, **kwargs):
        instance = self.instance()
        self.update_instance(instance, data, self.exclude_fields)
        instance.full_clean()
        instance.save()
        self.logger.info("Instance [%d] updated", instance.pk)
        return self.GET(request, data, *args, **kwargs)

    def DELETE(self, request, data, *args, **kwargs):
        instance = self.instance()
        pk = instance.pk
        instance.delete()
        self.logger.info("Instance [%d] removed", pk)
        return self.json_response("")


class CollectionView(JSONRestView):
    method_names = ['GET', 'POST']

    model = None
    exclude_fields = []

    def queryset(self):
        return self.model.objects.all()

    def GET(self, request, data, *args, **kwargs):
        return self.json_response(
            list(self.qs_to_dict_iter(self.queryset(), self.exclude_fields)))

    def POST(self, request, data, *args, **kwargs):
        instance = self.model()
        self.update_instance(instance, data, self.exclude_fields)
        instance.full_clean()
        instance.save()
        self.logger.info("Instance [%d] created", instance.pk)
        return self.json_response(
            self.instance_to_dict(instance, self.exclude_fields))


class UserResourceView(ResourceView):
    """
    Filter resource queryset for request user entries
    """
    def queryset(self):
        return super(UserResourceView,
                     self).queryset().filter(user=self.request.user_uniq)


class UserCollectionView(CollectionView):
    """
    Filter collection queryset for request user entries
    """
    def queryset(self):
        return super(UserCollectionView,
                     self).queryset().filter(user=self.request.user_uniq)

    def POST(self, request, data, *args, **kwargs):
        instance = self.model()
        self.update_instance(instance, data, self.exclude_fields)
        instance.user = request.user_uniq
        instance.full_clean()
        instance.save()
        self.logger.info("Instance [%d] created", instance.pk)
        return self.json_response(
            self.instance_to_dict(instance, self.exclude_fields))
