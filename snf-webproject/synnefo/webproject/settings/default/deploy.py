# Deployment settings
##################################

DEBUG = False
TEMPLATE_DEBUG = False

# Use secure cookie for django sessions cookie, change this if you don't plan
# to deploy applications using https
SESSION_COOKIE_SECURE = True

# You should always change this setting.
# Make this unique, and don't share it with anybody.
SECRET_KEY = 'ly6)mw6a7x%n)-e#zzk4jo6f2=uqu!1o%)2-(7lo+f9yd^k^bg'

# A boolean that specifies whether to use the X-Forwarded-Host header in
# preference to the Host header. This should only be enabled if a proxy which
# sets this header is in use.
USE_X_FORWARDED_HOST = True

# Settings / Cookies / Headers that should be 'cleansed'
HIDDEN_SETTINGS = 'SECRET|PASSWORD|PROFANITIES_LIST|SIGNATURE|AMQP_HOSTS|'\
                  'PRIVATE_KEY|DB_CONNECTION|TOKEN'
HIDDEN_COOKIES = ['password', '_pithos2_a', 'token', 'sessionid', 'shibstate',
                  'shibsession', 'CSRF_COOKIE']
HIDDEN_HEADERS = ['HTTP_X_AUTH_TOKEN', 'HTTP_COOKIE']
# Mail size limit for unhandled exception
MAIL_MAX_LEN = 100 * 1024 # (100KB)

#When set to True, if the request URL does not match any of the patterns in the
#URLconf and it doesn't end in a slash, an HTTP redirect is issued to the same
#URL with a slash appended. Note that the redirect may cause any data submitted
#in a POST request to be lost. Due to the REST nature of most of the registered
#Synnefo endpoints we prefer to disable this behaviour by default.
APPEND_SLASH = False
