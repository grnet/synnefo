import pkg_resources


def get_dist_from_module(modname):
    pkgroot = pkg_resources.get_provider(modname).egg_root
    return list(pkg_resources.find_distributions(pkgroot))[0]


def get_dist(dist_name):
    return pkg_resouces.get_distribution(dist_name)


def get_dist_version(dist_name):
    """
    Get the version for the specified distribution name
    """
    try:
        return get_dist(dist_name).version
    except Exception, e:
        return 'unknown'


def get_component_version(modname):
    """
    Return the version of a synnefo module/package based on its
    corresponding distributed package version
    """
    try:
        return get_dist_from_module(modname).version
    except Exception, e:
        return 'unknown'


def vcs_info():
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
    desc = callgit('git describe')

    return branch, revid, revno, desc


def vcs_version():
    """
    Package version based on `git describe`, compatible with setuptools
    version format
    """
    return vcs_info()[3].replace('v', '')

