
class Physical(object):

    def derive_description(self, commission_spec):
        """Derive a target physical description from a commission specification
           which is understandable and executable by the physical layer.
        """
        raise NotImplementedError

    def initiate_commission(self, serial, description):
        """Start creating a resource with a physical description,
           tagged by the given serial.
        """
        raise NotImplementedError

    def get_current_state(self, serial, description):
        """Query and return the current physical state for the
           target physical description initiated by the given serial.
        """
        raise NotImplementedError

    def complies(self, state, description):
        """Compare current physical state and target physical description
           and decide if the commission has been successfully implemented.
        """
        raise NotImplementedError

    def attainable(self, state, description):
        """Compare current physical state and target physical description
           and decide if the commission can be implemented.
        """
        raise NotImplementedError

    def continue_commission(self, serial, description):
        """Continue an ongoing commission towards
           the given target physical description
        """
        raise NotImplementedError

    def end_commission(self, serial, description):
        """Cancel and stop tracking the commission identified by serial"""
        raise NotImplementedError

