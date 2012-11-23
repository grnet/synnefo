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

from imp import find_module, load_module

_modules = {}

def imp_module(fullname):
    if fullname in _modules:
        return _modules[fullname]

    components = fullname.split('.')
    if not components:
        raise ValueError('invalid module name')

    module = None
    modulepath = []

    for name in components:
        if not name:
            raise ValueError("Relative paths not allowed")

        modulepath.append(name)
        modulename = '.'.join(modulepath)
        if modulename in _modules:
            module = _modules[modulename]

        elif hasattr(module, name):
            module = getattr(module, name)

        elif not hasattr(module, '__path__'):
            m = find_module(name)
            module = load_module(modulename, *m)

        else:
            try:
                m = find_module(name, module.__path__)
                module = load_module(modulename, *m)
            except ImportError:
                m = "No module '%s' in '%s'" % (name, module.__path__)
                raise ImportError(m)

        _modules[modulename] = module

    return module


def list_modules():
    return sorted(_modules.keys())


