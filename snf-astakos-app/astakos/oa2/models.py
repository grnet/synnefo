import datetime
import urlparse

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

CLIENT_TYPES = (
    ('confidential', _('Confidential')),
    ('public', _('Public'))
)

CONFIDENTIAL_TYPES = ['confidential']

TOKEN_TYPES = (('Basic', _('Basic')),
               ('Bearer', _('Bearer')))

GRANT_TYPES = (('authorization_code', _('Authorization code')),
               ('password', _('Password')),
               ('client_credentials', _('Client Credentials')))

ACCESS_TOKEN_TYPES = (('online', _('Online token')),
                      ('offline', _('Offline token')))


class RedirectUrl(models.Model):
    client = models.ForeignKey('oa2.Client', on_delete=models.PROTECT)
    is_default = models.BooleanField(default=True)
    url = models.URLField(unique=True)

    class Meta:
        ordering = ('is_default', )
        unique_together = ('client', 'url',)


class Client(models.Model):
    name = models.CharField(max_length=100)
    identifier = models.CharField(max_length=255, unique=True)
    secret = models.CharField(max_length=255, null=True, default=None)
    url = models.CharField(max_length=255)
    type = models.CharField(max_length=100, choices=CLIENT_TYPES,
                            default='confidential')
    is_trusted = models.BooleanField(default=False)

    def save(self, **kwargs):
        if self.secret is None and self.type == 'confidential':
            raise ValidationError("Confidential clients require a secret")
        super(Client, self).save(**kwargs)

    def requires_auth(self):
        return self.type in CONFIDENTIAL_TYPES

    def get_default_redirect_uri(self):
        return self.redirecturl_set.get().url

    def redirect_uri_is_valid(self, uri):
        # ignore user specific uri part
        parts = list(urlparse.urlsplit(uri))
        path = parts[2]
        pieces = path.rsplit('/', 3)
        parts[2] = '/'.join(pieces[:-3]) if len(pieces) > 3 else path
        uri = urlparse.urlunsplit(parts)

        # TODO: handle trailing slashes
        return self.redirecturl_set.filter(url=uri).count() > 0

    def get_id(self):
        return self.identifier


class AuthorizationCode(models.Model):
    user = models.ForeignKey('im.AstakosUser', on_delete=models.PROTECT)
    code = models.TextField()
    redirect_uri = models.CharField(max_length=255, null=True, default=None)
    client = models.ForeignKey('oa2.Client', on_delete=models.PROTECT)
    scope = models.TextField(null=True, default=None)
    created_at = models.DateTimeField(default=datetime.datetime.now())

    access_token = models.CharField(max_length=100, choices=ACCESS_TOKEN_TYPES,
                                    default='online')

    # not really useful
    state = models.TextField(null=True, default=None)

    def client_id_is_valid(self, client_id):
        return self.client_id == client_id

    def redirect_uri_is_valid(self, redirect_uri, client):
        return (self.redirect_uri == redirect_uri and
                client.redirect_uri_is_valid(redirect_uri))

    def __repr__(self):
        return ("Authorization code: %s "
                "(user: %s, client: %s, redirect_uri: %s, scope: %s)" % (
                    self.code,
                    self.user.log_display,
                    self.client.get_id(),
                    self.redirect_uri, self.scope))


class Token(models.Model):
    code = models.TextField()
    created_at = models.DateTimeField(default=datetime.datetime.now())
    expires_at = models.DateTimeField()
    token_type = models.CharField(max_length=100, choices=TOKEN_TYPES,
                                  default='Bearer')
    grant_type = models.CharField(max_length=100, choices=GRANT_TYPES,
                                  default='authorization_code')

    # authorization fields
    user = models.ForeignKey('im.AstakosUser', on_delete=models.PROTECT)
    redirect_uri = models.CharField(max_length=255)
    client = models.ForeignKey('oa2.Client', on_delete=models.PROTECT)
    scope = models.TextField(null=True, default=None)
    access_token = models.CharField(max_length=100, choices=ACCESS_TOKEN_TYPES,
                                    default='online')

    # not really useful
    state = models.TextField(null=True, default=None)

    def __repr__(self):
        return ("Token: %s (token_type: %s, grant_type: %s, "
                "user: %s, client: %s, scope: %s)" % (
                    self.code, self.token_type, self.grant_type,
                    self.user.log_display, self.client.get_id(), self.scope))
