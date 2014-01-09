from django.conf import settings


def get_setting(key, default):
    return getattr(settings, 'OAUTH2_%s' % key, default)

USER_MODEL = get_setting('USER_MODEL', 'auth.User')

ENDPOINT_PREFIX = get_setting('ENDPOINT_PREFIX', 'oauth2/')

TOKEN_ENDPOINT = get_setting('TOKEN_ENDPOINT', 'token/')

AUTHORIZATION_ENDPOINT = get_setting('AUTHORIZATION_ENDPOINT', 'auth/')

# Set the length of newly created authorization codes to 60 characters
AUTHORIZATION_CODE_LENGTH = get_setting('AUTHORIZATION_CODE_LENGTH', 60)

# Set the length of newly created access tokens to 30 characters
TOKEN_LENGTH = get_setting('TOKEN_LENGTH', 30)

# Set the expiration time of newly created access tokens to 20 seconds
TOKEN_EXPIRES = get_setting('TOKEN_EXPIRES', 20)

# Set the maximum allowed redirection endpoint URI length
# Requests for a greater redirection endpoint URI will fail.
MAXIMUM_ALLOWED_REDIRECT_URI_LENGTH = get_setting(
    'MAXIMUM_ALLOWED_REDIRECT_URI_LENGTH', 5000)
