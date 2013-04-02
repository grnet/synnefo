"""
"""

from django.http import HttpResponse
from collections import namedtuple


class ClientBase(object):

    def auth_methods(self):
        pass


def authorize(request):
    pass

def token(request):
    pass

def redirect(request):
    pass
