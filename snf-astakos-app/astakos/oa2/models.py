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

import datetime

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
    url = models.TextField()

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
        for redirect_uri in self.redirecturl_set.values_list('url', flat=True):
            if uri == redirect_uri:
                return True
            elif uri.startswith(redirect_uri.rstrip('/') + '/'):
                return True
        return False

    def get_id(self):
        return self.identifier


class AuthorizationCode(models.Model):
    user = models.ForeignKey('im.AstakosUser', on_delete=models.PROTECT)
    code = models.TextField()
    redirect_uri = models.TextField(null=True, default=None)
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
                "(user: %r, client: %r, redirect_uri: %r, scope: %r)" % (
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
    redirect_uri = models.TextField()
    client = models.ForeignKey('oa2.Client', on_delete=models.PROTECT)
    scope = models.TextField(null=True, default=None)
    access_token = models.CharField(max_length=100, choices=ACCESS_TOKEN_TYPES,
                                    default='online')

    # not really useful
    state = models.TextField(null=True, default=None)

    def __repr__(self):
        return ("Token: %r (token_type: %r, grant_type: %r, "
                "user: %r, client: %r, scope: %r)" % (
                    self.code, self.token_type, self.grant_type,
                    self.user.log_display, self.client.get_id(), self.scope))
