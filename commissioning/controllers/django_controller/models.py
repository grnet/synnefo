
from commissioning import Controller

from django.db.models import Model, BigIntegerField, CharField, IntegerField
from django.db import transaction
from json import dumps as json_dumps, loads as json_loads


class ControllerCommission(Model):

    serial = BigIntegerField(primary_key=True)
    clientkey = CharField(null=False, max_length=72)
    physical_description = CharField(null=False, max_length=4096)
    status = IntegerField(null=False)


class DjangoController(Controller):

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
        physical_description = json_dumps(physical_description)
        create = ControllerCommission.objects.create
        create( serial=serial, clientkey=clientkey,
                physical_description=physical_description )

    def get_commission(self, serial):
        """Retrieve the commission registered with serial"""
        try:
            commission = ControllerCommission.objects.get(serial=serial)
        except ControllerCommission.DoesNotExist:
            return None

        return (commission.serial,
                commission.clientkey,
                commission.physical_description,
                commission.status)

    def complete_commission(self, serial):
        """Mark and commit in stable storage the commission identified by
           a serial as to-be-completed-successfully,
           i.e that it has succeeded in producing a physical resource
           and is to be removed from being tracked by the holder server,
           controller, and physical layers.
        """
        commission = ControllerCommission.objects.get(serial=serial)
        commission.status = 1
        commission.save()

    def is_commission_complete(self, serial):
        """Return true if the serial is marked as
           completed by complete_commission()
        """
        commission = ControllerCommission.objects.get(serial=serial)
        return commission.status > 0

    def fail_commission(self, serial):
        """Mark and commit in stable storage the commission identified by
           a serial as to-be-completed-unsuccessfully,
           i.e. that it has failed in producing a physical resource
           and is to be removed from being tracked by the holder server,
           controller, and physical layers.
        """
        commission = ControllerCommission.objects.get(serial=serial)
        commission.status = -1
        commission.save()

    def is_commission_failing(self, serial):
        """Return true if the serial is marked as
           failing by fail_commission()
        """
        commission = ControllerCommission.objects.get(serial=serial)
        return commission.status < 0

    def retire_commission(self, serial):
        """Stop tracking the commission identified by a serial"""

        try:
            commission = ControllerCommission.objects.get(serial=serial)
        except ControllerCommission.DoesNotExist:
            return

        commission.delete()

