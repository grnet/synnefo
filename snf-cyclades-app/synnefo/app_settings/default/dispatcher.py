DISPATCHER_FORMATTERS = {
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
    'default': {
        'format': '%(asctime)s %(name)s %(module)s [%(levelname)s] %(message)s'
    },
}

DISPATCHER_LOGGING_SETUP = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters':  DISPATCHER_FORMATTERS,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
        'file': {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': '/var/log/synnefo/dispatcher.log',
            'formatter': 'default'
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'INFO'
        },
        'dispatcher': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False
        },
    }
}

#DISPATCHER_LOGGING_SETUP['loggers']['synnefo.logic'] = {
#    'level': 'INFO',
#    'propagate': False
#}
#DISPATCHER_LOGGING_SETUP['loggers']['amqp'] = {
#    'level': 'INFO',
#   'propagate': False
#}
