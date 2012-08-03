
from commissioning import Physical
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


class FSCrudPhysical(Physical):

    def __init__(self, queuepath, dataroot, *args, **kw):
        physical_identity = kw.pop('physical_identity', 'one')
        self.physical_init(queuepath, dataroot, physical_identity)
        super(FSCrudPhysical, self).__init__(*args[2:], **kw)

    def physical_init(self, queuepath, dataroot, identity):
        self.queuepath = queuepath
        self.dataroot = dataroot
        self.identity = identity

    def derive_description(self, commission_spec):
        """Derive a target physical description from a commission specification
           which is understandable and executable by the physical layer.
        """

        command = commission_spec['call_name']
        call_data = commission_spec['call_data']

        desc = {
                'path'      :   call_data['path'],
                'dataspec'  :   call_data['dataspec'],
        }

        if command == 'DELETE':
            desc['path'] = ''
        elif command == 'READ':
            desc['dataspec'] = None

        return desc

    def initiate_commission(self, serial, description):
        """Start creating a resource with a physical description,
           tagged by the given serial.
        """
        queuepath = self.queuepath
        jobpath = path_join(queuepath, str(serial))
        jobpath_new = path_join(queuepath, 'new',  self.identity)
        with open(jobpath_new, "w") as f:
            f.write(json_dumps(physical_description))

        move(jobpath_new, jobpath)

    def get_current_state(self, serial, description):
        """Query and return the current physical state for the
           target physical description initiated by the given serial.
        """

        path = description['path']
        datapath = path_join(self.dataroot, path)
        offset, spec_content = description['dataspec']

        current_state = {
                'path'      :   '',
                'dataspec'  :   '',
                'error'     :   ''
        }

        try:
            with open(datapath, "r") as f:
                f.seek(offset)
                content = f.read(len(spec_content))
        except (OSError, IOError), e:
            current_state['error'] = str(e)[:256]
        else:
            current_state['path'] = path
            current_state['dataspec'] = (offset, content)

        return current_state

    def complies(self, state, description):
        """Compare current physical state and target physical description
           and decide if the commission has been successfully implemented.
        """
        if state['error']:
            return 0

        if state['path'] != description['path']:
            return 0

        if state['dataspec'] != description['dataspec']:
            return 0

        return 1

    def attainable(self, state, description):
        """Compare current physical state and target physical description
           and decide if the commission can be implemented.
        """
        if state['path'] != description['path']:
            return 0

        if state['error']:
            return 0

        return 1

    def continue_commission(self, serial, description):
        """Continue an ongoing commission towards
           the given target physical description"""
        return self.initiate_commission(serial, description)

    def end_commission(self, serial):
        """Cancel and stop tracking the commission tagged by serial"""
        pass

