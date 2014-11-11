# filelocker.py - Cross-platform (posix/nt) API for flock-style file locking.
#                 Requires python 1.5.2 or better.
"""Cross-platform (posix/nt) API for flock-style file locking.


Synopsis:

    import filelocker
    with filelocker.lock("lockfile", filelocker.LOCK_EX):
        print "Got it"


Methods:

   lock ( file, flags, tries=10 )


Constants:

   LOCK_EX
   LOCK_SH
   LOCK_NB


Exceptions:

    LockException


Notes:

For the 'nt' platform, this module requires the Python Extensions for Windows.
Be aware that this may not work as expected on Windows 95/98/ME.


History:

I learned the win32 technique for locking files from sample code
provided by John Nielsen <nielsenjf@my-deja.com> in the documentation
that accompanies the win32 modules.


Author: Jonathan Feinberg <jdf@pobox.com>,
        Lowell Alleman <lalleman@mfps.com>
Version: $Id: filelocker.py 5474 2008-05-16 20:53:50Z lowell $


Modified to work as a contextmanager

"""

import os
from contextlib import contextmanager


class LockException(Exception):
    # Error codes:
    LOCK_FAILED = 1


# Import modules for each supported platform
if os.name == 'nt':
    import win32con
    import win32file
    import pywintypes
    LOCK_EX = win32con.LOCKFILE_EXCLUSIVE_LOCK
    LOCK_SH = 0  # the default
    LOCK_NB = win32con.LOCKFILE_FAIL_IMMEDIATELY
    # is there any reason not to reuse the following structure?
    __overlapped = pywintypes.OVERLAPPED()
elif os.name == 'posix':
    import fcntl
    LOCK_EX = fcntl.LOCK_EX
    LOCK_SH = fcntl.LOCK_SH
    LOCK_NB = fcntl.LOCK_NB
else:
    raise RuntimeError("FileLocker only defined for nt and posix platforms")


# --------------------------------------
# Implementation for NT
if os.name == 'nt':
    @contextmanager
    def lock(filename, flags):
        file = open(filename, "w+")
        hfile = win32file._get_osfhandle(file.fileno())

        try:
            win32file.LockFileEx(hfile, flags, 0, -0x10000, __overlapped)
            try:
                yield
            finally:
                file.close()
        except pywintypes.error, exc_value:
            # error: (33, 'LockFileEx',
            #         'The process cannot access the file because another
            #          process has locked a portion of the file.')
            file.close()
            if exc_value[0] == 33:
                raise LockException(LockException.LOCK_FAILED, exc_value[2])
            else:
                # Q:  Are there exceptions/codes we should be dealing with?
                raise


# --------------------------------------
# Implementation for Posix
elif os.name == 'posix':
    @contextmanager
    def lock(filename, flags):
        file = open(filename, "w+")

        try:
            fcntl.flock(file.fileno(), flags)
            try:
                yield
            finally:
                file.close()
        except IOError, exc_value:
            #  IOError: [Errno 11] Resource temporarily unavailable
            file.close()
            if exc_value[0] == 11:
                raise LockException(LockException.LOCK_FAILED, exc_value[1])
            else:
                raise
