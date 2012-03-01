#
# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import base64
import binascii
import re

from hashlib import md5

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db.models.signals import pre_save

try:
    from paramiko import rsakey, dsskey, SSHException
except:
    pass


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
    content = models.TextField()
    fingerprint = models.CharField(max_length=100, null=False, blank=True)

    class Meta:
        app_label = 'userdata'

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
        elif key_type == "ssh-dss":
            key = dsskey.DSSKey(data=data)
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

    @classmethod
    def user_limit_exceeded(cls, user):
        return (PublicKeyPair.objects.filter(user=user).count() >=
                settings.USERDATA_MAX_SSH_KEYS_PER_USER)
