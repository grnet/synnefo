#
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

import base64
import binascii
import re
import datetime

from hashlib import md5

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.core.validators import MaxLengthValidator
from django.db.models.signals import pre_save

try:
    from paramiko import rsakey, dsskey, SSHException
except:
    pass

SSH_KEY_MAX_CONTENT_LENGTH = getattr(settings,
                                     'USERDATA_SSH_KEY_MAX_CONTENT_LENGTH',
                                     30000)


class ProfileModel(models.Model):
    """
    Abstract model, provides a basic interface for models that store
    user specific information
    """

    user = models.CharField(max_length=100)

    class Meta:
        abstract = True
        app_label = 'userdata'


class PublicKeyPair(ProfileModel):
    """
    Public key model
    """
    name = models.CharField(max_length=255, null=False, blank=False)
    content = models.TextField(validators=[
        MaxLengthValidator(SSH_KEY_MAX_CONTENT_LENGTH)])
    fingerprint = models.CharField(max_length=100, null=False, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Type field should take values between ssh and x509
    # Django does not currently support
    # SQL ENUM type so we wiil just use
    # a plain CharField
    type = models.CharField(max_length=10, null=False, default='ssh')

    class Meta:
        app_label = 'userdata'
        unique_together = ('user', 'name')

    def full_clean(self, *args, **kwargs):
        # update fingerprint before clean
        self.update_fingerprint()
        super(PublicKeyPair, self).full_clean(*args, **kwargs)

    def key_data(self):
        return self.content.split(" ", 1)

    def get_key_object(self):
        """
        Identify key contents and return appropriate paramiko public key object
        """
        key_type, data = self.key_data()
        data = base64.b64decode(data)

        if key_type == "ssh-rsa":
            key = rsakey.RSAKey(data=data)
            self.type = 'ssh'
        elif key_type == "ssh-dss":
            key = dsskey.DSSKey(data=data)
            self.type = 'x509'
        else:
            raise Exception("Invalid key type")

        return key

    def clean_key(self):
        key = None
        try:
            key = self.get_key_object()
        except:
            raise ValidationError("Invalid SSH key")

    def clean(self):
        if PublicKeyPair.user_limit_exceeded(self.user):
            raise ValidationError("SSH keys limit exceeded.")

    def update_fingerprint(self):
        try:
            fp = binascii.hexlify(self.get_key_object().get_fingerprint())
            self.fingerprint = ":".join(re.findall(r"..", fp))
        except:
            self.fingerprint = "unknown fingerprint"

    def save(self, *args, **kwargs):
        self.update_fingerprint()
        super(PublicKeyPair, self).save(*args, **kwargs)

    # NOTE: `deleted` and `deleted_at` properties will not affect the database
    # for now since, they are False and null respectively. For the sake of
    # compatibility, we will trivially return these properties in the
    # object layer. If changes are to be made, we can change them into fields
    @property
    def deleted(self):
        return False

    @property
    def deleted_at(self):
        return None

    @classmethod
    def user_limit_exceeded(cls, user):
        return (PublicKeyPair.objects.filter(user=user).count() >=
                settings.USERDATA_MAX_SSH_KEYS_PER_USER)
