from django.conf import settings


def get_setting(key, default):
    return getattr(settings, 'OA2_%s' % key, default)

USER_MODEL = get_setting('USER_MODEL', 'auth.User')
