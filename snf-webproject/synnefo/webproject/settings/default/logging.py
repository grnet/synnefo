# Setup logging (use this name for the setting to avoid conflicts with django > 1.2.x).
LOGGING_SETUP = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'simple': {
            'format': '%(message)s'
        },
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] %(name)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'class': 'logging.FileHandler',
            'formatter': 'verbose',

        },
    },
    'loggers': {
        'root': {
            'handlers': ['console', 'file'],
            'level': 'INFO'
        },
    }
}

