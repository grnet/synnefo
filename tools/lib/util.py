import os

DEFAULT_HOST = 'plus.pithos.grnet.gr'
DEFAULT_API = 'v1'
DEFAULT_USER = 'test'
DEFAULT_AUTH = '0000'

def get_user():
    try:
        return os.environ['PITHOS_USER']
    except KeyError:
        return DEFAULT_USER

def get_auth():
    try:
        return os.environ['PITHOS_AUTH']
    except KeyError:
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
