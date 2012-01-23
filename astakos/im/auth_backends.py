from django.conf import settings
from django.contrib.auth.backends import ModelBackend
#from django.core.exceptions import ImproperlyConfigured
#from django.db.models import get_model

from astakos.im.models import AstakosUser

class AstakosUserModelCredentialsBackend(ModelBackend):
    """
    AuthenticationBackend used to authenticate user creadentials
    """
    def authenticate(self, username=None, password=None):
        try:
            user = AstakosUser.objects.get(username=username)
            if user.check_password(password):
                return user
        except AstakosUser.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return AstakosUser.objects.get(pk=user_id)
        except AstakosUser.DoesNotExist:
            return None
    
    #@property
    #def user_class(self):
    #    if not hasattr(self, '_user_class'):
    #        #self._user_class = get_model(*settings.CUSTOM_USER_MODEL.split('.', 2))
    #        self._user_class = get_model('astakos.im', 'astakosuser')
    #        print '#', self._user_class
    #        if not self._user_class:
    #            raise ImproperlyConfigured('Could not get custom user model')
    #    return self._user_class

class AstakosUserModelTokenBackend(ModelBackend):
    """
    AuthenticationBackend used to authenticate using token instead
    """
    def authenticate(self, username=None, auth_token=None):
        try:
            user = AstakosUser.objects.get(username=username)
            if user.auth_token == auth_token:
                return user
        except AstakosUser.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return AstakosUser.objects.get(pk=user_id)
        except AstakosUser.DoesNotExist:
            return None