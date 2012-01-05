VERSION = (0, 8, 0, 'alpha', 0)
__version__ = VERSION

def get_version():
    """
    Utility to parse version tuple to string
    """
    version = '%s.%s' % (VERSION[0], VERSION[1])
    if VERSION[2]:
        version = '%s.%s' % (version, VERSION[2])
    if VERSION[3:] == ('alpha', 0):
        version = '%s pre-alpha' % version
    else:
        if VERSION[3] != 'final':
            version = '%s %s %s' % (version, VERSION[3], VERSION[4])
    return version

def vcs_version():
    """
    Return current git HEAD commit information
    """
    import subprocess
    callgit = lambda(cmd): subprocess.Popen(
            ['/bin/sh', '-c', cmd],
            stdout=subprocess.PIPE).communicate()[0].strip()

    branch = callgit('git branch | grep -Ei "\* (.*)" | cut -f2 -d" "')
    revid = callgit("git --no-pager log --max-count=1 | cut -f2 -d' ' | head -1")
    revno = callgit('git --no-pager log --oneline | wc -l')

    return branch, revid, revno

