#
# snf-cyclades-app logging configuration
#####################

DISPATCHER_LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,

    'formatters': {
        'simple': {
            'format': '%(asctime)s [%(levelname)s] %(message)s'
        },
        'verbose': {
            'format': '%(asctime)s [%(process)d] %(name)s %(module)s [%(levelname)s] %(message)s'
        },
        'django': {
            'format': '[%(asctime)s] %(levelname)s %(message)s',
            'datefmt': '%d/%b/%Y %H:%M:%S'
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
        'handlers': ['file'],
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

