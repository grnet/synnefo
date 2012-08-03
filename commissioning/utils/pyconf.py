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
        if k in variables:
            opts[k] = variables[k]

    return opts

def pyconf_vars(filename, variables):
    variables.update(pyconf(filename, variables.keys()))

