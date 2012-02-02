from django.contrib.auth.backends import ModelBackend
from django.core.validators import email_re

from astakos.im.models import AstakosUser

class TokenBackend(ModelBackend):
    """
    AuthenticationBackend used to authenticate using token instead
    """
    def authenticate(self, email=None, auth_token=None):
        try:
            user = AstakosUser.objects.get(email=email)
            if user.auth_token == auth_token:
                return user
        except AstakosUser.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return AstakosUser.objects.get(pk=user_id)
        except AstakosUser.DoesNotExist:
            return None

class EmailBackend(ModelBackend):
    """
    If the ``username`` parameter is actually an email uses email to authenticate
    the user else tries the username.
    
    Used from ``astakos.im.forms.LoginForm`` to authenticate.
    """
    def authenticate(self, username=None, password=None):
        #If username is an email address, then try to pull it up
        if email_re.search(username):
            try:
                user = AstakosUser.objects.get(email=username)
            except AstakosUser.DoesNotExist:
                return None
        else:
            #We have a non-email address username we
            #should try username
            try:
                user = AstakosUser.objects.get(username=username)
            except AstakosUser.DoesNotExist:
                return None
        if user.check_password(password):
            return user
    
    def get_user(self, user_id):
        try:
            return AstakosUser.objects.get(pk=user_id)
        except AstakosUser.DoesNotExist:
            return None