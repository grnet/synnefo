import urllib
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

    def __init__(self, method, GET=None, POST=None, META=None, secure=False,
                 user=None):
        self.method = method

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
        parents = [b for b in bases if isinstance(b, BackendBase)]
        meta = attrs.pop('Meta', None)
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
    endpoints_prefix = '/oa2/'

    token_endpoint = 'token/'
    token_length = 30
    token_expires = 3600

    authorization_endpoint = 'auth/'
    authorization_code_length = 60
    authorization_response_types = ['code', 'token']

    grant_types = ['authorization_code', 'implicit']

    response_cls = Response
    request_cls = Request

    client_model = Client
    token_model = Token
    code_model = AuthorizationCode
    user_model = User

    def __init__(self, base_url='', endpoints_prefix='/oa2/', id='oa2',
                 **kwargs):
        self.base_url = base_url
        self.endpoints_prefix = endpoints_prefix
        self.id = id
        self._errors_to_http = kwargs.get('errors_to_http', True)

    # Request/response builders
    def build_request(self, method, get, post, meta):
        return self.request_cls(method=method, GET=get, POST=post, META=meta)

    def build_response(self, status, headers=None, body=''):
        return self.response_cls(status=status, headers=headers, body=body)

    # ORM Methods
    def create_authorization_code(self, client, code, redirect_uri, scope,
                                  state, **kwargs):
        code_params = {
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client.get_id(),
            'scope': scope,
            'state': state
        }
        code_params.update(kwargs)
        return self.code_model.create(code, **code_params)

    def _token_params(self, value, token_type, client, scope):
        created_at = datetime.datetime.now()
        expires = self.token_expires
        expires_at = created_at + datetime.timedelta(seconds=expires)
        token_params = {
            'token': value,
            'token_type': token_type,
            'client': client,
            'scope': scope,
            'created_at': created_at,
            'expires': expires,
            'expires_at': expires_at
        }
        return token_params

    def create_token(self, value, token_type, client, scope, refresh=False):
        params = self._token_params(value, token_type, client, scope)
        if refresh:
            refresh_token = self.generate_token()
            params['refresh_token'] = refresh_token
            # TODO: refresh token expires ???
        token = self.token_model.create(value, **params)

    def delete_authorization_code(self, code):
        del self.code_model.ENTRIES[code]

    def get_client_by_id(self, client_id):
        return self.client_model.get(client_id)

    def get_client_by_credentials(self, username, password):
        return None

    def get_authorization_code(self, code):
        return self.code_model.get(code)

    def get_client_authorization_code(self, client, code):
        code_instance = self.get_authorization_code(code)
        if not code_instance:
            raise OA2Error("Invalid code", code)

        if client.id != code_instance.client_id:
            raise OA2Error("Invalid code for client", code, client)
        return code_instance

    def client_id_exists(self, client_id):
        return bool(self.get_client_by_id(client_id))

    def build_site_url(self, prefix='', **params):
        params = urllib.urlencode(params)
        return "%s%s%s%s" % (self.base_url, self.endpoints_prefix, prefix,
                             params)

    def _get_uri_base(self, uri):
        split = urlparse.urlsplit(uri)
        return "%s://%s%s" % (split.scheme, split.netloc, split.path)

    def build_client_redirect_uri(self, client, uri, **params):
        if not client.redirect_uri_is_valid(uri):
            raise OA2Error("Invalid redirect uri")
        params = urllib.urlencode(params)
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

    #
    # Response helpers
    #

    def grant_accept_response(self, client, redirect_uri, scope, state,
                              request):
        context = {'client': client.get_id(), 'redirect_uri': redirect_uri,
                   'scope': scope, 'state': state, 'url': url}
        json_content = json.dumps(context)
        return self.response_cls(status=200, body=json_content)

    def build_redirect_to_login_response(self, request):
        return Response(302, headers={'Location': '/login'})

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

    def grant_authorization_code(self, user, client, code, redirect_uri,
                                 scope):
        code = self.get_client_authorization_code(client, code)
        if code.scope != scope:
            raise OA2Error("Invalid scope")
        token = self.add_token_for_client(client, "Bearer", code.scope,
                                          refresh=True)
        self.delete_authorization_code(code.code)
        return token


    #
    # Helpers
    #

    def _get_credentials(self, params, headers):
        if 'HTTP_AUTHORIZATION' in headers:
            scheme, b64credentials = headers.get(
                'HTTP_AUTHORIZATION').split(" ")
            credentials = b64decode(b64credentials).split(":")
            return scheme, credentials
        else:
            return None, None
        pass

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
    # Parameters validation methods
    #

    def validate_client(params, meta, requires_auth=False):
        raise OA2Error("Invalid client")

    def validate_redirect_uri(client, params, headers, allow_default=True):
        raise OA2Error("Invalid redirect uri")

    def validate_state(params, meta):
        raise OA2Error("Invalid state")

    def validate_scope(client, params, headers):
        raise OA2Error("Invalid state")

    #
    # Requests validation methods
    #

    def validate_code_request(params, headers):
        client = self.validate_client(params, headers, False)
        redirect_uri = self.validate_redirect_uri(client, params, headers)
        scope = self.validate_scope(client, params, headers)
        state = self.validate_state(client, params, headers)
        return client, redirect_uri, scope, state

    def validate_token_request(params, headers):
        client = self.validate_client(params, headers, False)
        redirect_uri = self.validate_redirect_uri(client, params, headers)
        scope = self.validate_scope(client, params, headers)
        state = self.validate_state(client, params, headers)
        return client, redirect_uri, scope, state

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

        if auth_type == 'code':
            client, uri, scope, state = \
                    self.validate_code_request(params, request.META)
        elif auth_type == 'token':
            client, uri, scope, state = \
                self.validate_token_request(params, request.META)
        else:
            #TODO: handle custom type
            raise OA2Error("Invalid authorization type")

        user = self.get_user_from_request(request)
        if not user:
            return self.redirect_to_login_response(request)

        if request.method == 'POST':
            if auth_type == 'code':
                return self.process_code_request(user, client, uri, scope,
                                                 state)
            elif auth_type == 'token':
                return self.process_code_request(user, client, uri, scope,
                                                 state)
            else:
                #TODO: handle custom type
                raise OA2Error("Invalid authorization type")
        else:
            return self.grant_accept_response()
