from os.path import exists

def pyconf(filename, keys=None):
    if not exists(filename):
        return {}

    execfile(filename)
    opts = {}
    variables = locals()
    if keys is None:
        keys = variables.keys()

    keyset = set(k for k in keys if (k and k[0] != '_' and k.isupper()))
    for k in keyset:
        opts[k] = variables[k]

    return opts

def pyconf_globals(filename):
    g = globals()
    g.update(pyconf(filename, g.keys()))

