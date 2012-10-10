# -*- coding: utf-8 -*-
#
# Logging configuration
##################################


FORMATTERS = {
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
}

LOGGING_SETUP = {
    'version': 1,
    'disable_existing_loggers': True,

    'formatters':  FORMATTERS,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'syslog': {
            'class': 'logging.handlers.SysLogHandler',
            'address': '/dev/log',
#            'address': ('localhost', 514),
            'facility': 'daemon',
            'formatter': 'verbose',
            'level': 'INFO',
        },
    },

    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO'
        },
        'synnefo': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': 0
        },
        'synnefo.admin': {
            'level': 'INFO',
            'propagate': 1
        },
        'synnefo.api': {
            'level': 'INFO',
            'propagate': 1
        },
        'synnefo.db': {
            'level': 'INFO',
            'propagate': 1
        },
        'synnefo.logic': {
            'level': 'INFO',
            'propagate': 1
        },
    }
}

SNF_MANAGE_LOGGING_SETUP = {
    'version': 1,
    'disable_existing_loggers': True,

    'formatters': FORMATTERS,

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },

    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO'
        },
        'synnefo': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': 0
        }
    }
}
