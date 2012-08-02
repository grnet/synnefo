#!/usr/bin/env python

from json import dumps as json_dumps, loads as json_loads
from os.path import join as path_join, exists, isdir
from os import listdir, makedirs, unlink
from shutil import move

def ensure_directory(dirpath):
    if not isdir(dirpath):
        if exists(dirpath):
            m = ("path '%s' exists but is not a directory!"
                    % (dirpath,)  )
            raise ValueError(m)

        makedirs(dirpath)

    try:
        test_path = path_join(dirpath, "__test")
        with open(test_path, "w") as f:
            f.write("test")
    except (OSError, IOError), e:
        m = "cannot create files in directory '%s'" % (dirpath,)
        raise ValueError(m)

    unlink(test_path)
    if exists(test_path):
        m = "'%s' exists after unlink" % (test_path,)
        raise ValueError(m)


class FSCrudServer(object):

    def __init__(self, queuepath, dataroot):
        err_path = path_join(queuepath, 'errs')
        succeed_path =  path_join(queuepath, 'succeeds')
        ensure_directory(queuepath)
        ensure_directory(dataroot)
        ensure_directory(err_path)
        ensure_directory(succeed_path)

        self.queuepath = queuepath
        self.dataroot = dataroot
        self.err_path = err_path
        self.succeed_path = succeed_path

        from pyinotify import WatchManager, Notifier, ProcessEvent, IN_MOVED_TO
        watch_manager = WatchManager()

        class EventProcessor(ProcessEvent):

            def __init__(self, backend):
                self.backend = backend

            def process_IN_MOVED_TO(self, event):
                path = event.path
                backend = self.backend
                if path != backend.queuepath:
                    m = "notification for unknown directory '%s'!" % (path,)
                    raise AssertionError(m)

                jobname = event.name
                backend.runjob(jobname)

            def process_IN_Q_OVERFLOW(self, event):
                raise RuntimError("BOOM :(")

        event_processor = EventProcessor(self)
        notifier = Notifier(watch_manager, event_processor)
        watch_descriptor = watch_manager.add_watch( queuepath,
                                                    IN_MOVED_TO,
                                                    rec=False   )
        self.watch_manager = watch_manager
        self.event_processor = event_processor
        self.notifier = notifier
        self.watch_descriptor = watch_descriptor

    def process_events(self):
        notifier = self.notifier
        if notifier.check_events():
            notifier.read_events()

        notifier.process_events()

    def event_loop(self):
        while 1:
            notifier = self.notifier
            if notifier.check_events(timeout=100):
                notifier.read_events()
            notifier.process_events()

    def process_all_jobs(self):
        jobnames = listdir(self.queuepath)
        runjob = self.runjob
        for jobname in jobnames:
            runjob(jobname)

    @classmethod
    def main(cls, argv):
        argc = len(argv)
        usage = """
Usage: ./fscrud_server queuepath=<queuepath> <dataroot> [loop|process]
"""

        args = []
        append = args.append
        kw = {
            'queuepath':    ".fscrud/queue",
            'dataroot':     ".fscrud/data",
        }

        for arg in argv[1:]:
            key, sep, val = arg.partition('=')
            if not sep:
                append(arg)
            else:
                kw[key] = val

        queuepath = kw['queuepath']
        dataroot = kw['dataroot']

        if not args:
            print(usage)
            raise SystemExit

        cmd = args[0]

        backend = cls(queuepath, dataroot)
        if cmd == 'loop':
            backend.event_loop()
        elif cmd == 'process':
            backend.process_all_jobs()
        else:
            raise ValueError("unknown command '%s'" % (cmd,))

    def do_runjob(self, jobpath):
        with open(jobpath) as f:
            job = json_loads(f.read())

        filepath = path_join(self.dataroot, job['path'])
        if '..' in filepath:
            raise ValueError("'..' not allowed in paths")

        dataspec = job['dataspec']
        if dataspec is None:
            # DELETE
            unlink(filepath)
            return

        offset, data = dataspec
        if data is None:
            # READ
            # Nothing to do here, read them yourself!
            pass

        if not exists(filepath):
            # CREATE
            with open(filepath, "w") as f:
                pass

        # UPDATE
        with open(filepath, "r+") as f:
            f.seek(offset)
            f.write(data)

    def runjob(self, jobname):
        jobpath = path_join(self.queuepath, jobname)
        try:
            self.do_runjob(jobpath)
        except Exception, e:
            print e
            move(jobpath, self.err_path)
        else:
            move(jobpath, self.suceed_path)


if __name__ == '__main__':
    import sys

    FSCrudServer.main(sys.argv)

