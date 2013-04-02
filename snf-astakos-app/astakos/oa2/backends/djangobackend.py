from astakos.oa2.backends import base as oa2base
from astakos.oa2.backends import base as errors
from astakos.oa2.models import *

from django.conf.urls.defaults import patterns, url
from django import http


class DjangoViewsMixin(object):

    def auth_view(self, request):
        oa2request = self.build_request(request)
        response = self.authorize(oa2request, accept=False)
        return self._build_response(response)

    def token_view(self, request):
        return http.HttpResponse("token view")


class DjangoBackendORMMixin(object):

    def get_client_by_credentials(self, username, password):
        try:
            return Client.objects.get(identifier=username, secret=password)
        except Client.DoesNotExist:
            raise errors.InvalidClientID("No such client found")

    def get_client_by_id(self, clientid):
        try:
            return Client.objects.get(identifier=clientid)
        except Client.DoesNotExist:
            raise errors.InvalidClientID("No such client found")

    def create_authorization_code(self, client, code, redirect_uri, scope,
                                  state, **kwargs):
        return AuthorizationCode.objects.create(**{
            'code': code,
            'client_id': client.get_id(),
            'redirect_uri': redirect_uri,
            'scope': scope,
            'state': state
        })

    def create_token(self, value, token_type, client, scope, refresh=False):
        params = self._token_params(value, token_type, client, scope)
        if refresh:
            refresh_token = self.generate_token()
            params['refresh_token'] = refresh_token
            # TODO: refresh token expires ???
        token = self.token_model.create(value, **params)

    def delete_authorization_code(self, code):
        del self.code_model.ENTRIES[code]


class DjangoBackend(DjangoBackendORMMixin, oa2base.SimpleBackend,
                    DjangoViewsMixin):

    code_model = AuthorizationCode

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
            'GET': django_request.GET,
            'POST': django_request.POST,
            'META': django_request.META,
            'secure': django_request.is_secure(),
        }
        if django_request.user.is_authenticated():
            params['user'] = django_request.user
        return oa2base.Request(**params)

    def get_url_patterns(self):
        _patterns = patterns(
            '',
            url(r'^%s/auth/?$' % self.endpoints_prefix, self.auth_view,
                name='%s_authenticate' % self.id),
            url(r'^%s/token/?$' % self.endpoints_prefix, self.token_view,
                name='%s_token' % self.id),
        )
        return _patterns


class AstakosBackend(DjangoBackend):
    pass
