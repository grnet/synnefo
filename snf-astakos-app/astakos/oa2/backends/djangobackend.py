import astakos.oa2.models as oa2_models

from astakos.oa2.backends import base as oa2base
from astakos.oa2.backends import base as errors

from django import http
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.core.urlresolvers import reverse
from django.conf.urls.defaults import patterns, url
from django.views.decorators.csrf import csrf_exempt

import logging
logger = logging.getLogger(__name__)


class DjangoViewsMixin(object):

    def auth_view(self, request):
        oa2request = self.build_request(request)
        oa2response = self.authorize(oa2request, accept=False)
        return self._build_response(oa2response)

    @csrf_exempt
    def token_view(self, request):
        oa2request = self.build_request(request)
        oa2response = self.grant_token(oa2request)
        return self._build_response(oa2response)


class DjangoBackendORMMixin(object):

    def get_client_by_credentials(self, username, password):
        try:
            return oa2_models.Client.objects.get(identifier=username,
                                                 secret=password)
        except oa2_models.Client.DoesNotExist:
            raise errors.InvalidClientID("No such client found")

    def get_client_by_id(self, clientid):
        try:
            return oa2_models.Client.objects.get(identifier=clientid)
        except oa2_models.Client.DoesNotExist:
            raise errors.InvalidClientID("No such client found")

    def get_authorization_code(self, code):
        try:
            return oa2_models.AuthorizationCode.objects.get(code=code)
        except oa2_models.AuthorizationCode.DoesNotExist:
            raise errors.OA2Error("No such authorization code")

    def get_token(self, token):
        try:
            return oa2_models.Token.objects.get(code=token)
        except oa2_models.Token.DoesNotExist:
            raise errors.OA2Error("No such token")

    def delete_authorization_code(self, code):
        code.delete()
        logger.info('%r deleted' % code)

    def delete_token(self, token):
        token.delete()
        logger.info('%r deleted' % token)

    def check_credentials(self, client, username, secret):
        if not (username == client.get_id() and secret == client.secret):
            raise errors.InvalidAuthorizationRequest("Invalid credentials")


class DjangoBackend(DjangoBackendORMMixin, oa2base.SimpleBackend,
                    DjangoViewsMixin):

    code_model = oa2_models.AuthorizationCode.objects
    token_model = oa2_models.Token.objects
    client_model = oa2_models.Client.objects

    def _build_response(self, oa2response):
        response = http.HttpResponse()
        response.status_code = oa2response.status
        response.content = oa2response.body
        for key, value in oa2response.headers.iteritems():
            response[key] = value
        return response

    def build_request(self, django_request):
        params = {
            'method': django_request.method,
            'path': django_request.path,
            'GET': django_request.GET,
            'POST': django_request.POST,
            'META': django_request.META,
            'secure': settings.DEBUG or django_request.is_secure(),
            #'secure': django_request.is_secure(),
        }
        # TODO: check for valid astakos user
        if django_request.user.is_authenticated():
            params['user'] = django_request.user
        return oa2base.Request(**params)

    def get_url_patterns(self):
        sep = '/' if self.endpoints_prefix else ''
        _patterns = patterns(
            '',
            url(r'^%s%sauth/?$' % (self.endpoints_prefix, sep),
                self.auth_view,
                name='%s_authenticate' % self.id),
            url(r'^%s%stoken/?$' % (self.endpoints_prefix, sep),
                self.token_view,
                name='%s_token' % self.id),
        )
        return _patterns

    def is_uri(self, string):
        validator = URLValidator()
        try:
            validator(string)
        except ValidationError:
            return False
        else:
            return True

    def get_login_uri(self):
        return reverse('login')


class AstakosBackend(DjangoBackend):
    pass
