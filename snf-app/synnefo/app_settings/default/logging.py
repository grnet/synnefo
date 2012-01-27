#
# snf-app logging configuration
#####################

DISPATCHER_LOGGING = {
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
        'file': {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': '/var/log/synnefo/dispatcher.log',
            'formatter': 'verbose',
            'level': 'DEBUG'
        },
    },

    'loggers': {
        'synnefo': {'propagate': 1}
    },

    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG',
    }
}


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

