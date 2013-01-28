# Copyright 2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from synnefo.lib.commissioning import (CallError, register_exception,
                                       InvalidDataError, CorruptedError)

@register_exception
class CommissionException(CallError):
    pass

@register_exception
class InvalidKeyError(CommissionException):
    pass

@register_exception
class NoEntityError(CommissionException):
    pass

@register_exception
class CommissionValueException(CommissionException):
    def __init__(self, *args, **kw):
        super(CommissionValueException, self).__init__(*args, **kw)
        kwargs = self.kwargs

        self.source    = kwargs['source']
        self.target    = kwargs['target']
        self.resource  = kwargs['resource']
        self.requested = kwargs['requested']
        self.current   = kwargs['current']
        self.limit     = kwargs['limit']

@register_exception
class NoQuantityError(CommissionValueException):
    pass

@register_exception
class NoCapacityError(CommissionValueException):
    pass

@register_exception
class ExportLimitError(CommissionValueException):
    pass

@register_exception
class ImportLimitError(CommissionValueException):
    pass

@register_exception
class DuplicateError(CommissionException):
    pass
