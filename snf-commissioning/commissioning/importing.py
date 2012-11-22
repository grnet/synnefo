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


