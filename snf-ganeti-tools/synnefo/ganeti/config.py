import os
import imp
import sys
import glob

def load(conf_dir): 
    """Takes a configuration file directory and interprets all *.conf files"""

    files = glob.glob(os.path.join(conf_dir, '*.conf'))

    for filename in sorted(files):
        if sys.version_info > (2, 6):
            # We are using a version that understands PYTHONDONTWRITEBYTECODE
            # so it is safe to use imp.load_source here
            module = imp.load_source(filename, filename)
            #CONFIG = getattr(module, 'CONFIG', None)
        else:
            module = {}
            execfile(filename, module)
            #CONFIG = module.get('CONFIG')

        return module
