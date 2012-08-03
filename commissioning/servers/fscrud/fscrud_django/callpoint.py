
from commissioning import ControlledCallpoint, get_callpoint, mkcallargs
from commissioning.controllers.django_controller \
    import Controller as DjangoController
from commissioning.specs.fscrud import API_Spec as FSCrudAPI
from commissioning.physicals.fscrud import FSCrudPhysical
from django.conf import settings


qh_callpoint = get_callpoint('clients.quotaholder', automake='http')
fscrud_api_spec = FSCrudAPI()

class FSCrudDjangoController(DjangoController):

    def controller_init(self):
        self.context = {}
        self.clientkey = 'fscrudck'
        self.entitykey = 'fscrudek'
        self.entityroot = 'fscrud'

    def get_commission_issue(self, commission_spec):
        call_data = commission_spec['call_data']
        path = call_data['path']
        args = mkcallargs (
                context     =   self.context,
                entity      =   path,
                key         =   self.entitykey,
                clientkey   =   self.clientkey,
                owner       =   self.entityroot,
                ownerkey    =   self.entitykey,
                provisions  =   [('access', 'path', 1)]
        )

        return args


class FSCrudControlled(ControlledCallpoint):

    api_spec = fscrud_api_spec

    def init_connection(self, connection):
        # ignore connection
        queuepath = settings.FSCRUD_QUEUE_PATH
        dataroot = settings.FSCRUD_DATA_ROOT
        physical = FSCrudPhysical(queuepath, dataroot)
        quotaholder = qh_callpoint('null://wherever/')
        self.controller = FSCrudDjangoController(quotaholder, physical)

    def commit(self):
        pass

    def rollback(self):
        pass

API_Callpoint = FSCrudControlled

