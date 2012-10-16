#
# snf-cyclades-app logging configuration
#####################

SNFADMIN_LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,

    'formatters': {
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] %(message)s'
        },
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },

    'loggers': {
        'synnefo': {'propagate': 1}
    },

    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    }
}

