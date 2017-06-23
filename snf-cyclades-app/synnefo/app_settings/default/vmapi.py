## -*- coding: utf-8 -*-
##

# Define cache for vmapi
VMAPI_CACHE = {
    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    "LOCATION": "",
    "KEY_PREFIX": "vmapi",
}

# Enable/disable resetting parameters
VMAPI_RESET_PARAMS = True
