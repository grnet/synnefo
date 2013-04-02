from django.db import models
from django.utils.translation import ugettext_lazy as _

from astakos.oa2 import settings

CLIENT_TYPES = (
    ('confidential', _('Confidential')),
    ('public', _('Public'))
)

CONFIDENTIAL_TYPES = ['confidential']


class RedirectUrl(models.Model):
    client = models.ForeignKey('oa2.Client')
    default = models.BooleanField(default=True)
    url = models.URLField(unique=True)

    class Meta:
        ordering = ('default', )


class Client(models.Model):
    name = models.CharField(max_length=100)
    identifier = models.CharField(max_length=255, unique=True)
    secret = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    type = models.CharField(max_length=100, choices=CLIENT_TYPES,
                            default='confidential')

    def requires_auth(self):
        return self.type in CONFIDENTIAL_TYPES

    def get_default_redirect_uri(self):
        return self.redirecturl_set.get().url

    def redirect_uri_is_valid(self, uri):
        return self.redirecturl_set.filter(url=uri).count() > 0

    def get_id(self):
        return self.identifier


class AuthorizationCode(models.Model):
    code = models.TextField()
    redirect_uri = models.CharField(max_length=255)
    client_id = models.CharField(max_length=255, db_index=True)
    scope = models.TextField()

    # not really useful
    state = models.TextField()


class Token(models.Model):
    code = models.TextField()
    expires_at = models.DateTimeField()
