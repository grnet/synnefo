# -*- coding: utf-8 -*-
#
# QUOTAHOLDER configuration
#####################

# URL of the Quotaholder
#
#
# Set to True to use the Quotaholder service. Otherwise, static
# limits are used
CYCLADES_USE_QUOTAHOLDER = False

CYCLADES_QUOTAHOLDER_URL = "http://127.0.0.1:8008/api/quotaholder/v"

CYCLADES_QUOTAHOLDER_TOKEN = ""

# Tune the size of the http pool for the quotaholder client.
# It limits the maximum number of quota-querying requests
# that Cyclades can serve. Extra requests will be blocked 
# until another has completed.
CYCLADES_QUOTAHOLDER_POOLSIZE = 200
