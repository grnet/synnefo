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

import urlparse
import uuid
import datetime
import json

from base64 import b64encode, b64decode
from hashlib import sha512


import logging
logger = logging.getLogger(__name__)


def handles_oa2_requests(func):
    def wrapper(self, *args, **kwargs):
        if not self._errors_to_http:
            return func(self, *args, **kwargs)
        try:
            return func(self, *args, **kwargs)
        except OA2Error, e:
            return self.build_response_from_error(e)
    return wrapper


class OA2Error(Exception):
    error = None


class InvalidClientID(OA2Error):
    pass


class NotAuthenticatedError(OA2Error):
    pass


class InvalidClientRedirectUrl(OA2Error):
    pass


class InvalidAuthorizationRequest(OA2Error):
    pass


class Response(object):

    def __init__(self, status, body='', headers=None,
                 content_type='plain/text'):
        if not body:
            body = ''
        if not headers:
            headers = {}

        self.status = status
        self.body = body
        self.headers = headers
        self.content_type = content_type

    def __repr__(self):
        return "%d RESPONSE (BODY: %r, HEADERS: %r)" % (self.status,
                                                        self.body,
                                                        self.headers)


class Request(object):

    def __init__(self, method, path, GET=None, POST=None, META=None,
                 secure=False, user=None):
        self.method = method
        self.path = path

        if not GET:
            GET = {}
        if not POST:
            POST = {}
        if not META:
            META = {}

        self.secure = secure
        self.GET = GET
        self.POST = POST
        self.META = META
        self.user = user

    def __repr__(self):
        prepend = ""
        if self.secure:
            prepend = "SECURE "
        return "%s%s REQUEST (POST: %r, GET:%r, HEADERS:%r, " % (prepend,
                                                                 self.method,
                                                                 self.POST,
                                                                 self.GET,
                                                                 self.META)


class ORMAbstractBase(type):

    def __new__(cls, name, bases, attrs):
        attrs['ENTRIES'] = {}
        return super(ORMAbstractBase, cls).__new__(cls, name, bases, attrs)


class ORMAbstract(object):

    ENTRIES = {}

    __metaclass__ = ORMAbstractBase

    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    @classmethod
    def create(cls, id, **params):
        params = cls.clean_params(params)
        params['id'] = id
        cls.ENTRIES[id] = cls(**params)
        return cls.get(id)

    @classmethod
    def get(cls, pk):
        return cls.ENTRIES.get(pk)

    @classmethod
    def clean_params(cls, params):
        return params


class Client(ORMAbstract):

    def get_id(self):
        return self.id

    def get_redirect_uris(self):
        return self.uris

    def get_default_redirect_uri(self):
        return self.uris[0]

    def redirect_uri_is_valid(self, redirect_uri):
        split = urlparse.urlsplit(redirect_uri)
        if split.scheme not in urlparse.uses_query:
            raise OA2Error("Invalid redirect url scheme")
        uris = self.get_redirect_uris()
        return redirect_uri in uris

    def requires_auth(self):
        if self.client_type == 'confidential':
            return True
        return 'secret' in dir(self)

    def check_credentials(self, username, secret):
        return username == self.id and secret == self.secret


class Token(ORMAbstract):

    def to_dict(self):
        params = {
            'access_token': self.token,
            'token_type': self.token_type,
            'expires_in': self.expires,
        }
        if self.refresh_token:
            params['refresh_token'] = self.refresh_token
        return params


class AuthorizationCode(ORMAbstract):
    pass


class User(ORMAbstract):
    pass


class BackendBase(type):

    def __new__(cls, name, bases, attrs):
        super_new = super(BackendBase, cls).__new__
        #parents = [b for b in bases if isinstance(b, BackendBase)]
        #meta = attrs.pop('Meta', None)
        return super_new(cls, name, bases, attrs)

    @classmethod
    def get_orm_options(cls, attrs):
        meta = attrs.pop('ORM', None)
        orm = {}
        if meta:
            for attr in dir(meta):
                orm[attr] = getattr(meta, attr)
        return orm


class SimpleBackend(object):

    __metaclass__ = BackendBase

    base_url = ''
    endpoints_prefix = 'oauth2/'

    token_endpoint = 'token/'
    token_length = 30
    token_expires = 20

    authorization_endpoint = 'auth/'
    authorization_code_length = 60
    authorization_response_types = ['code', 'token']

    grant_types = ['authorization_code']

    response_cls = Response
    request_cls = Request

    client_model = Client
    token_model = Token
    code_model = AuthorizationCode
    user_model = User

    def __init__(self, base_url='', endpoints_prefix='oauth2/', id='oauth2',
                 token_endpoint='token/', token_length=30,
                 token_expires=20, authorization_endpoint='auth/',
                 authorization_code_length=60,
                 redirect_uri_limit=5000, **kwargs):
        self.base_url = base_url
        self.endpoints_prefix = endpoints_prefix
        self.token_endpoint = token_endpoint
        self.token_length = token_length
        self.token_expires = token_expires
        self.authorization_endpoint = authorization_endpoint
        self.authorization_code_length = authorization_code_length
        self.id = id
        self._errors_to_http = kwargs.get('errors_to_http', True)
        self.redirect_uri_limit = redirect_uri_limit

    # Request/response builders
    def build_request(self, method, get, post, meta):
        return self.request_cls(method=method, GET=get, POST=post, META=meta)

    def build_response(self, status, headers=None, body=''):
        return self.response_cls(status=status, headers=headers, body=body)

    # ORM Methods
    def create_authorization_code(self, user, client, code, redirect_uri,
                                  scope, state, **kwargs):
        code_params = {
            'code': code,
            'redirect_uri': redirect_uri,
            'client': client,
            'scope': scope,
            'state': state,
            'user': user
        }
        code_params.update(kwargs)
        code_instance = self.code_model.create(**code_params)
        logger.info(u'%r created' % code_instance)
        return code_instance

    def _token_params(self, value, token_type, authorization, scope):
        created_at = datetime.datetime.now()
        expires = self.token_expires
        expires_at = created_at + datetime.timedelta(seconds=expires)
        token_params = {
            'code': value,
            'token_type': token_type,
            'created_at': created_at,
            'expires_at': expires_at,
            'user': authorization.user,
            'redirect_uri': authorization.redirect_uri,
            'client': authorization.client,
            'scope': authorization.scope,
        }
        return token_params

    def create_token(self, value, token_type, authorization, scope,
                     refresh=False):
        params = self._token_params(value, token_type, authorization, scope)
        if refresh:
            refresh_token = self.generate_token()
            params['refresh_token'] = refresh_token
            # TODO: refresh token expires ???
        token = self.token_model.create(**params)
        logger.info(u'%r created' % token)
        return token

#    def delete_authorization_code(self, code):
#        del self.code_model.ENTRIES[code]

    def get_client_by_id(self, client_id):
        return self.client_model.get(client_id)

    def get_client_by_credentials(self, username, password):
        return None

    def get_authorization_code(self, code):
        return self.code_model.get(code)

    def get_client_authorization_code(self, client, code):
        code_instance = self.get_authorization_code(code)
        if not code_instance:
            raise OA2Error("Invalid code")

        if client.get_id() != code_instance.client.get_id():
            raise OA2Error("Mismatching client with code client")
        return code_instance

    def client_id_exists(self, client_id):
        return bool(self.get_client_by_id(client_id))

    def build_site_url(self, prefix='', **params):
        params = self.urlencode(params)
        return "%s%s%s%s" % (self.base_url, self.endpoints_prefix, prefix,
                             params)

    def _get_uri_base(self, uri):
        split = urlparse.urlsplit(uri)
        return "%s://%s%s" % (split.scheme, split.netloc, split.path)

    def build_client_redirect_uri(self, client, uri, **params):
        if not client.redirect_uri_is_valid(uri):
            raise OA2Error("Invalid redirect uri")
        params = self.urlencode(params)
        uri = self._get_uri_base(uri)
        return "%s?%s" % (uri, params)

    def generate_authorization_code(self):
        dg64 = b64encode(sha512(str(uuid.uuid4())).hexdigest())
        return dg64[:self.authorization_code_length]

    def generate_token(self, *args, **kwargs):
        dg64 = b64encode(sha512(str(uuid.uuid4())).hexdigest())
        return dg64[:self.token_length]

    def add_authorization_code(self, user, client, redirect_uri, scope, state,
                               **kwargs):
        code = self.generate_authorization_code()
        self.create_authorization_code(user, client, code, redirect_uri, scope,
                                       state, **kwargs)
        return code

    def add_token_for_client(self, token_type, authorization, refresh=False):
        token = self.generate_token()
        self.create_token(token, token_type, authorization, refresh)
        return token

    #
    # Response helpers
    #

    def grant_accept_response(self, client, redirect_uri, scope, state):
        context = {'client': client.get_id(), 'redirect_uri': redirect_uri,
                   'scope': scope, 'state': state,
                   #'url': url,
                   }
        json_content = json.dumps(context)
        return self.response_cls(status=200, body=json_content)

    def grant_token_response(self, token, token_type):
        context = {'access_token': token, 'token_type': token_type,
                   'expires_in': self.token_expires}
        json_content = json.dumps(context)
        return self.response_cls(status=200, body=json_content)

    def redirect_to_login_response(self, request, params):
        parts = list(urlparse.urlsplit(request.path))
        parts[3] = self.urlencode(params)
        query = {'next': urlparse.urlunsplit(parts)}

        parts[2] = self.get_login_uri()
        parts[3] = self.urlencode(query)
        return Response(302, headers={'Location':  urlparse.urlunsplit(parts)})

    def redirect_to_uri(self, redirect_uri, code, state=None):
        parts = list(urlparse.urlsplit(redirect_uri))
        params = dict(urlparse.parse_qsl(parts[3], keep_blank_values=True))
        params['code'] = code
        if state is not None:
            params['state'] = state
        parts[3] = self.urlencode(params)
        return Response(302, headers={'Location': urlparse.urlunsplit(parts)})

    def build_response_from_error(self, exception):
        response = Response(400)
        logger.exception(exception)
        error = 'generic_error'
        if exception.error:
            error = exception.error
        body = {
            'error': error,
            'exception': exception.message,
        }
        response.body = json.dumps(body)
        response.content_type = "application/json"
        return response

    #
    # Processor methods
    #

    def process_code_request(self, user, client, uri, scope, state):
        code = self.add_authorization_code(user, client, uri, scope, state)
        return self.redirect_to_uri(uri, code, state)

    #
    # Helpers
    #

    def grant_authorization_code(self, client, code_instance, redirect_uri,
                                 scope=None, token_type="Bearer"):
        if scope and code_instance.scope != scope:
            raise OA2Error("Invalid scope")
        if self.normalize(redirect_uri) != \
                self.normalize(code_instance.redirect_uri):
            raise OA2Error("The redirect uri does not match "
                           "the one used during authorization")
        token = self.add_token_for_client(token_type, code_instance)
        self.delete_authorization_code(code_instance)  # use only once
        return token, token_type

    def consume_token(self, token):
        token_instance = self.get_token(token)
        if datetime.datetime.now() > token_instance.expires_at:
            self.delete_token(token_instance)  # delete expired token
            raise OA2Error("Token has expired")
        # TODO: delete token?
        return token_instance

    def _get_credentials(self, params, headers):
        if 'HTTP_AUTHORIZATION' in headers:
            scheme, b64credentials = headers.get(
                'HTTP_AUTHORIZATION').split(" ")
            if scheme != 'Basic':
                # TODO: raise 401 + WWW-Authenticate
                raise OA2Error("Unsupported authorization scheme")
            credentials = b64decode(b64credentials).split(":")
            return scheme, credentials
        else:
            return None, None
        pass

    def _get_authorization(self, params, headers, authorization_required=True):
        scheme, client_credentials = self._get_credentials(params, headers)
        no_authorization = scheme is None and client_credentials is None
        if authorization_required and no_authorization:
            raise OA2Error("Missing authorization header")
        return client_credentials

    def get_redirect_uri_from_params(self, client, params, default=True):
        """
        Accepts a client instance and request parameters.
        """
        redirect_uri = params.get('redirect_uri', None)
        if not redirect_uri and default:
            redirect_uri = client.get_default_redirect_uri()
        else:
            # TODO: sanitize redirect_uri (self.clean_redirect_uri ???)
            # clean and validate
            if not client.redirect_uri_is_valid(redirect_uri):
                raise OA2Error("Invalid client redirect uri")
        return redirect_uri

    #
    # Request identifiers
    #

    def identify_authorize_request(self, params, headers):
        return params.get('response_type'), params

    def identify_token_request(self, headers, params):
        content_type = headers.get('CONTENT_TYPE')
        if content_type != 'application/x-www-form-urlencoded':
            raise OA2Error("Invalid Content-Type header")
        return params.get('grant_type')

    #
    # Parameters validation methods
    #

    def validate_client(self, params, meta, requires_auth=True,
                        client_id_required=True):
        client_id = params.get('client_id')
        if client_id is None and client_id_required:
            raise OA2Error("Client identification is required")

        client_credentials = None
        try:  # check authorization header
            client_credentials = self._get_authorization(
                params, meta, authorization_required=False)
        except:
            pass
        else:
            if client_credentials is not None:
                _client_id = client_credentials[0]
                if client_id is not None and client_id != _client_id:
                    raise OA2Error("Client identification conflicts "
                                   "with client authorization")
                client_id = _client_id

        if client_id is None:
            raise OA2Error("Missing client identification")

        client = self.get_client_by_id(client_id)

        if requires_auth and client.requires_auth():
            if client_credentials is None:
                raise OA2Error("Client authentication is required")

        if client_credentials is not None:
            self.check_credentials(client, *client_credentials)
        return client

    def validate_redirect_uri(self, client, params, headers,
                              allow_default=True, is_required=False,
                              expected_value=None):
        redirect_uri = params.get('redirect_uri')
        if is_required and redirect_uri is None:
            raise OA2Error("Missing redirect uri")
        if redirect_uri is not None:
            if not bool(urlparse.urlparse(redirect_uri).scheme):
                raise OA2Error("Redirect uri should be an absolute URI")
            if len(redirect_uri) > self.redirect_uri_limit:
                raise OA2Error("Redirect uri length limit exceeded")
            if not client.redirect_uri_is_valid(redirect_uri):
                raise OA2Error("Mismatching redirect uri")
            if expected_value is not None and \
                    self.normalize(redirect_uri) != \
                    self.normalize(expected_value):
                raise OA2Error("Invalid redirect uri")
        else:
            try:
                redirect_uri = client.redirecturl_set.values_list('url',
                                                                  flat=True)[0]
            except IndexError:
                raise OA2Error("Unable to fallback to client redirect URI")
        return redirect_uri

    def validate_state(self, client, params, headers):
        return params.get('state')
        #raise OA2Error("Invalid state")

    def validate_scope(self, client, params, headers):
        scope = params.get('scope')
        if scope is not None:
            scope = scope.split(' ')[0]  # keep only the first
        # TODO: check for invalid characters
        return scope

    def validate_code(self, client, params, headers):
        code = params.get('code')
        if code is None:
            raise OA2Error("Missing authorization code")
        return self.get_client_authorization_code(client, code)

    #
    # Requests validation methods
    #

    def validate_code_request(self, params, headers):
        client = self.validate_client(params, headers, requires_auth=False)
        redirect_uri = self.validate_redirect_uri(client, params, headers)
        scope = self.validate_scope(client, params, headers)
        scope = scope or redirect_uri  # set default
        state = self.validate_state(client, params, headers)
        return client, redirect_uri, scope, state

    def validate_token_request(self, params, headers, requires_auth=False):
        client = self.validate_client(params, headers)
        redirect_uri = self.validate_redirect_uri(client, params, headers)
        scope = self.validate_scope(client, params, headers)
        scope = scope or redirect_uri  # set default
        state = self.validate_state(client, params, headers)
        return client, redirect_uri, scope, state

    def validate_code_grant(self, params, headers):
        client = self.validate_client(params, headers,
                                      client_id_required=False)
        code_instance = self.validate_code(client, params, headers)
        redirect_uri = self.validate_redirect_uri(
            client, params, headers,
            expected_value=code_instance.redirect_uri)
        return client, redirect_uri, code_instance

    #
    # Endpoint methods
    #

    @handles_oa2_requests
    def authorize(self, request, **extra):
        """
        Used in the following cases
        """
        if not request.secure:
            raise OA2Error("Secure request required")

        # identify
        request_params = request.GET
        if request.method == "POST":
            request_params = request.POST

        auth_type, params = self.identify_authorize_request(request_params,
                                                            request.META)

        if auth_type is None:
            raise OA2Error("Missing authorization type")
        if auth_type == 'code':
            client, uri, scope, state = \
                self.validate_code_request(params, request.META)
        elif auth_type == 'token':
            raise OA2Error("Unsupported authorization type")
#            client, uri, scope, state = \
#                self.validate_token_request(params, request.META)
        else:
            #TODO: handle custom type
            raise OA2Error("Invalid authorization type")

        user = getattr(request, 'user', None)
        if not user:
            return self.redirect_to_login_response(request, params)

        if request.method == 'POST':
            if auth_type == 'code':
                return self.process_code_request(user, client, uri, scope,
                                                 state)
            elif auth_type == 'token':
                raise OA2Error("Unsupported response type")
#                return self.process_token_request(user, client, uri, scope,
#                                                 state)
            else:
                #TODO: handle custom type
                raise OA2Error("Invalid authorization type")
        else:
            if client.is_trusted:
                return self.process_code_request(user, client, uri, scope,
                                                 state)
            else:
                return self.grant_accept_response(client, uri, scope, state)

    @handles_oa2_requests
    def grant_token(self, request, **extra):
        """
        Used in the following cases
        """
        if not request.secure:
            raise OA2Error("Secure request required")

        grant_type = self.identify_token_request(request.META, request.POST)

        if grant_type is None:
            raise OA2Error("Missing grant type")
        elif grant_type == 'authorization_code':
            client, redirect_uri, code = \
                self.validate_code_grant(request.POST, request.META)
            token, token_type = \
                self.grant_authorization_code(client, code, redirect_uri)
            return self.grant_token_response(token, token_type)
        elif (grant_type in ['client_credentials', 'token'] or
              self.is_uri(grant_type)):
            raise OA2Error("Unsupported grant type")
        else:
            #TODO: handle custom type
            raise OA2Error("Invalid grant type")

    @staticmethod
    def urlencode(params):
        raise NotImplementedError

    @staticmethod
    def normalize(url):
        raise NotImplementedError
