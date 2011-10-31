from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS

from synnefo.db import models as synnefo_models

User = synnefo_models.SynnefoUser

class ProfileModel(models.Model):
    """
    Abstract model, provides a basic interface for models that store
    user specific information
    """

    user = models.ForeignKey(User)

    class Meta:
        abstract = True
        app_label = 'userdata'


class PublicKeyPair(ProfileModel):
    """
    Public key model
    """
    name = models.CharField(max_length=255, null=False, blank=False)
    content = models.TextField()

    class Meta:
        app_label = 'userdata'

    def clean(self):
        if PublicKeyPair.user_limit_exceeded(self.user):
            raise ValidationError("SSH keys limit exceeded.")

    @classmethod
    def user_limit_exceeded(cls, user):
        return PublicKeyPair.objects.filter(user=user).count() >= settings.USERDATA_MAX_SSH_KEYS_PER_USER
