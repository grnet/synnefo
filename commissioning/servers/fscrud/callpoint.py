
from commissioning import ControlledCallpoint, get_callpoint
from commissioning.controllers.django_controller \
    import Controller as DjangoController
from commissioning.specs.fscrud import API_Spec as FSCrudAPI
from commissioning.physicals.fscrud import FSCrudPhysical


qh_callpoint = get_callpoint('clients.quotaholder', automake='http')

class FSCrudControlled(ControlledCallpoint):

    api_spec = FSCrudAPI()

    def init_connection(self, connection):
        physical = FSCrudPhysical(connection)
        quotaholder = qh_callpoint('null://wherever/')
        self.controller = DjangoController(quotaholder, physical)

API_Callpoint = FSCrudControlled
