import os

#DEFAULT_HOST = 'pithos.dev.grnet.gr'
DEFAULT_HOST = '127.0.0.1:8000'
DEFAULT_API = 'v1'
DEFAULT_USER = 'test'
DEFAULT_AUTH = '0000'

def get_user():
    return DEFAULT_USER

def get_auth():
    return DEFAULT_AUTH

def get_server():
    try:
        return os.environ['PITHOS_SERVER']
    except KeyError:
        return DEFAULT_HOST

def get_api():
    try:
        return os.environ['PITHOS_API']
    except KeyError:
        return DEFAULT_API