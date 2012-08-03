from .exception import CorruptedError
from .callpoint import Callpoint
from .physical import Physical
from .specificator import CanonifyException

class Controller(object):

    def __init__(self, quotaholder, physical):
        self.quotaholder = quotaholder
        self.physical = physical
        self.controller_init()

    def controller_init(self):
        pass

    def get_commission_issue(self, commission_spec):
        """Prepare and return the arguments for the
           quotaholder's issue_commission call,
           containing the provisions required and
           the target entity for their allocation.
        """
        raise NotImplementedError

    def register_commission(self,   serial,
                                    clientkey,
                                    physical_description    ):

        """Register a commission to the controller's stable storage,
           along with the quotaholder serial and clientkey,
           and the target physical description.
           This information is needed to co-ordinate the commission
           execution among the quotaholder server, the controller,
           and the physical layer implementing the resource.
        """
        raise NotImplementedError

    def get_commission(self, serial):
        """Retrieve the commission registered with serial"""
        raise NotImplementedError

    def complete_commission(self, serial):
        """Mark and commit in stable storage the commission identified by
           a serial as to-be-completed-successfully,
           i.e that it has succeeded in producing a physical resource
           and is to be removed from being tracked by the holder server,
           controller, and physical layers.
        """
        raise NotImplementedError

    def is_commission_complete(self, serial):
        """Return true if the serial is marked as
           completed by complete_commission()
        """
        raise NotImplementedError

    def fail_commission(self, serial):
        """Mark and commit in stable storage the commission identified by
           a serial as to-be-completed-unsuccessfully,
           i.e. that it has failed in producing a physical resource
           and is to be removed from being tracked by the holder server,
           controller, and physical layers.
        """
        raise NotImplementedError

    def is_commission_failing(self, serial):
        """Return true if the serial is marked as
           failing by fail_commission()
        """
        raise NotImplementedError

    def retire_commission(self, serial):
        """Stop tracking the commission identified by a serial"""
        raise NotImplementedError

    def undertake_commission(self, commission_spec):
        """Initiate and start tracking and co-ordinating a commission
           from a commission spec.
        """
        holder = self.quotaholder
        physical = self.physical

        commission_issue = self.get_commission_issue(commission_spec)
        entity = commission_issue['entity']
        clientkey = commission_issue['clientkey']
        physical_description = physical.derive_description(commission_spec)

        serial = holder.issue_commission(**commission_issue)
        self.register_commission(   serial,
                                    clientkey,
                                    physical_description    )

        self.process_controller(serial)
        return serial

    def process_controller(self, serial):
        """Consider the current state of a commission in the controller layer,
           and schedule next actions.
        """
        holder = self.quotaholder
        physical = self.physical
        controller = self

        r = controller.get_commission(serial)
        if not r:
            return

        serial, clientkey, physical_description, status = r

        if controller.is_commission_complete(serial):
            holder.accept_commission(serial=serial, clientkey=clientkey)
            physical.end_commission(serial, physical_description)
            controller.retire_commission(serial)

        elif controller.is_commission_failing(serial):
            holder.recall_commission(serial=serial, clientkey=clientkey)
            physical.end_commission(serial, physical_description)
            controller.retire_commission(serial)

        else:
            controller.process_physical(serial)

    def process_physical(self, serial):
        """Consider the current state of a commission in the physical layer,
           and schedule next actions.
        """
        physical = self.physical

        r = self.get_commission(serial)
        if not r:
            m = "Unknown serial %d in process_physical!" % (serial,)
            raise CorruptedError(m)

        target_description = r[2]
        current_state = physical.get_current_state(serial, target_description)

        if not current_state:

            physical.initiate_commission(serial, target_description)

        elif physical.complies(current_state, target_description):

            self.complete_commission(serial)
            self.process_controller(serial)

        elif physical.attainable(current_state, target_description):

            physical.continue_commission(serial, target_description)

        else:
            self.fail_commission(serial)
            physical.end_commission(serial, target_description)
            self.process_controller(serial)


class ControlledCallpoint(Callpoint):

    controllables = set()

    def __init__(self, *args):
        self.controllables = set()
        super(ControlledCallpoint, self).__init__(*args)

    def commission_from_call(self, call_name, call_data):
        commission_spec = {}
        commission_spec['call_name'] = call_name
        commission_spec['call_data'] = call_data
        commission_spec['provisions'] = ()
        return commission_spec, True

    def register_controllable(self, call_name):
        controllables = self.controllables
        if call_name in controllables:
            return

        canonify_output = self.api_spec.canonify_output
        if (canonify_output(call_name, None) is not None or
            not isinstance(canonify_output(call_name, 1L), long)):
                m = ("Attempt to register controllable call '%s', "
                     "but the api spec does not define a "
                     "nullable long (serial) output!" % (call_name,))
                raise CanonifyException(m)

        if not isinstance(canonify_output(call_name, 2**63), long):
            m = ("Attempt to register controllable call '%s', "
                 "but the api spec does not define a nullable long "
                 "(serial) output with a range up to 2**63!" % (call_name,))
            raise CanonifyException(m)

        controllables.add(call_name)

    def do_make_call(self, call_name, call_data):
        r = self.commission_from_call(call_name, call_data)
        commission_spec, controllable = r
        controller = self.controller

        if not controllable:
            return controller.forward_commission(commission_spec)

        if call_name not in self.controllables:
            self.register_controllable(call_name)

        serial = controller.undertake_commission(commission_spec)
        return serial

