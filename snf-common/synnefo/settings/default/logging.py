# -*- coding: utf-8 -*-
#
# Logging configuration
##################################

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,

    'formatters': {
        'simple': {
            'format': '%(message)s'
        },
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] %(message)s'
        },
        'django': {
            'format': '[%(asctime)s] %(levelname)s %(message)s',
            'datefmt': '%d/%b/%Y %H:%M:%S'
        },
    },

    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'django'
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
        'synnefo': {
            'handlers': ['syslog'],
            'level': 'INFO'
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

