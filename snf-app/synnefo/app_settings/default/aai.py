# -*- coding: utf-8 -*-
from synnefo.util.entry_points import extend_list_from_entry_point
#
# AAI configuration
#####################

# Unauthenticated HTTP requests to the UI get redirected to this URL
LOGIN_URL = "/login"

# Set the expiration time of newly created auth tokens
# to be this many hours after their creation time.
AUTH_TOKEN_DURATION = 30 * 24

# Enable receiving a temporary auth token (using the ?test URL parameter) that
# bypasses the authentication mechanism.
#
# Make sure there is an actual user in the db whose token matches
# BYPASS_AUTHENTICATION_SECRET_TOKEN.
#
# WARNING, ACHTUNG, README, etc: DO NOT ENABLE THIS ON DEPLOYED VERSIONS!
#
BYPASS_AUTHENTICATION = False
BYPASS_AUTHENTICATION_SECRET_TOKEN = '5e41595e9e884543fa048e07c1094d74'

# Urls that bypass Shibboleth authentication
AAI_SKIP_AUTH_URLS = ['/api', '/plankton']
AAI_SKIP_AUTH_URLS = extend_list_from_entry_point(AAI_SKIP_AUTH_URLS, \
        'synnefo', 'web_skip_urls')
