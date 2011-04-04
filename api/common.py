#
# Copyright (c) 2010 Greek Research and Technology Network
#

from synnefo.api.faults import BadRequest
from synnefo.api.util import api_method


@api_method()
def not_found(request):
    raise BadRequest('Not found.')

@api_method()
def method_not_allowed(request):
    raise BadRequest('Method not allowed.')
