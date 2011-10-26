from django.db import models
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
