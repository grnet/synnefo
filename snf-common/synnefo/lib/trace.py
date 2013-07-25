# Copyright 2013 GRNET S.A. All rights reserved.
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


def set_signal_trap():
    from os import getpid
    from traceback import format_stack, print_exc
    from signal import signal, SIGTRAP
    from sys import stderr
    import gc

    def greenlet_trace(arg):
        i = 0
        stderr.write("--- Greenlet trace: %s\n" % arg)
        for ob in gc.get_objects():
            if not isinstance(ob, greenlet):
                continue
            if not ob:
                continue
            i = i + 1
            stderr.write(("--- > Greenlet %d:\n" % i +
                          "".join(format_stack(ob.gr_frame)) + "\n\n"))
        stderr.write("--- End of trace: %s\n" % arg)

    try:
        from greenlet import greenlet
    except ImportError:

        def greenlet_trace(arg):
            return

    def handle_trap(*args):
        try:
            import trap_inject
            reload(trap_inject)
            trap_inject.inject()
        except ImportError:
            pass
        except:
            print_exc()

        msg = ('=== pid: %s' % getpid()) + '\n'.join(format_stack()) + '\n'
        stderr.write(msg)
        greenlet_trace('TRAP')

    signal(SIGTRAP, handle_trap)
