import pkg_resources
import os

def get_dist_from_module(modname):
    pkgroot = pkg_resources.get_provider(modname).egg_root
    return list(pkg_resources.find_distributions(pkgroot))[0]


def get_dist(dist_name):
    return pkg_resources.get_distribution(dist_name)


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
        try:
            return __import__('synnefo.versions.%s' % modname,
                    fromlist=['synnefo.versions']).__version__
        except ImportError:
            return  vcs_version()
    except Exception, e:
        return 'unknown'


def vcs_info():
    """
    Return current git HEAD commit information
    """
    import subprocess
    callgit = lambda(cmd): subprocess.Popen(
            ['/bin/sh', '-c', cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).communicate()[0].strip()

    branch = callgit('git branch | grep -Ei "\* (.*)" | cut -f2 -d" "')
    revid = callgit("git --no-pager log --max-count=1 | cut -f2 -d' ' | head -1")
    revno = callgit('git --no-pager log --oneline | wc -l')
    desc = callgit('git describe --tags')

    return branch, revid, revno, desc


def vcs_version():
    """
    Package version based on `git describe`, compatible with setuptools
    version format
    """
    return "-".join(vcs_info()[3].lstrip('v').split("-")[:-1])


def update_version(module, name='version', root="."):
    """
    Helper util to generate/replace a version.py file containing version
    information retrieved from vcs_version as a submodule of passed `module`
    """

    # exit early if not in development environment
    if not os.path.exists(os.path.join(root, '..', '.git')):
        return

    paths = [root] + module.split(".") + ["%s.py" % name]
    module_filename = os.path.join(*paths)
    content = """
__version__ = "%(version)s"
__version_info__ = __version__.split(".")
    """ % dict(version=vcs_version())

    module_file = file(module_filename, "w+")
    module_file.write(content)
    module_file.close()

