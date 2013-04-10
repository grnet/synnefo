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

# Settings / cookies that should be 'cleansed'
HIDDEN_SETTINGS = 'SECRET|PASSWORD|PROFANITIES_LIST|SIGNATURE|AMQP_HOSTS|PRIVATE_KEY|DB_CONNECTION'
HIDDEN_COOKIES  = '_pithos2_a|token|sessionid|shibstate|shibsession|CSRF_COOKIE'
