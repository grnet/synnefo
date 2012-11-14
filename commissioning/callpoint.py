
from .specificator  import  CanonifyException
from .exception     import  CorruptedError, InvalidDataError
from .importing     import  imp_module

from re import compile as re_compile, sub as re_sub

class Callpoint(object):

    api_spec = None

    CorruptedError = CorruptedError
    InvalidDataError = InvalidDataError

    original_calls = {}

    def __init__(self, connection=None):
        from json import loads, dumps

        self.json_loads = loads
        self.json_dumps = dumps
        self.init_connection(connection)
        original_calls = self.original_calls
        canonifier = self.api_spec

        if canonifier is None:
            m = "No api spec given to '%s'" % (type(self).__name__,)
            raise NotImplementedError(m)

        for call_name, call_doc in canonifier.call_docs():
            if hasattr(self, call_name):
                # don't crash: wrap the function instead
                #m = (   "Method '%s' defined both in natively "
                #        "in callpoint '%s' and in api spec '%s'" %
                #            (call_name,
                #             type(self).__name__,
                #             type(canonifier).__name__)             )

                #raise ValueError(m)
                call_func = getattr(self, call_name)
                if not callable(call_func):
                    m = (   "api spec '%s', method '%s' is not a "
                            "callable attribute in callpoint '%s'" % 
                            (   type(canonifier).__name__,
                                call_name,
                                type(self).__name       )           )
                    raise ValueError(m)

                original_calls[call_name] = call_func

            def mk_call_func():
                local_call_name = call_name
                def call_func(**data):
                    return self.make_call(local_call_name, data)

                call_func.__name__ = call_name
                call_func.__doc__ = call_doc
                return call_func

            setattr(self, call_name, mk_call_func())

    def init_connection(self, connection):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def do_make_call(self, call_name, data):
        raise NotImplementedError

    def validate_call(self, call_name):
        return hasattr(self, call_name)

    def make_call_from_json_description(self, json_description):
        try:
            description = self.json_loads(json_description)
        except ValueError, e:
            m = "Cannot load json description"
            raise self.InvalidDataError(m)

        data = self.make_call_from_description(description)
        json_data = self.json_dumps(data) if data is not None else None
        return json_data

    def make_call_from_description(self, description):
        try:
            call_name = description['call_name']
            call_data = description['call_data']
        except (TypeError, KeyError), e:
            m = "Invalid description"
            raise self.InvalidDataError(m, e)

        return self.make_call(call_name, call_data)

    def make_call_from_json(self, call_name, json_data):
        if json_data:
            try:
                data = self.json_loads(json_data)
            except ValueError, e:
                m = "Cannot load json data"
                raise self.InvalidDataError(m, e)
        else:
            data = None

        data = self.make_call(call_name, data)
        json_data = self.json_dumps(data) if data is not None else None
        return json_data

    def make_call(self, call_name, data):
        if call_name.startswith('_'):
            m = "Invalid call '%s'" % (call_name,)
            raise self.InvalidDataError(m)

        canonifier = self.api_spec
        try:
            data = canonifier.canonify_input(call_name, data)
        except CanonifyException, e:
            m = "Invalid input to call '%s'" % (call_name,)
            raise self.InvalidDataError(m, e)

        if not self.validate_call(call_name):
            m = "Cannot find specified call '%s'" % (call_name,)
            raise self.CorruptedError(m)

        call_func = self.original_calls.get(call_name, None)
        try:
            if call_func is None:
                data = self.do_make_call(call_name, data)
            else:
                data = call_func(**data)
        except Exception, e:
            self.rollback()
            raise
        else:
            self.commit()

        try:
            data = canonifier.canonify_output(call_name, data)
        except CanonifyException, e:
            m = "Invalid output from call '%s'" % (call_name,)
            raise self.CorruptedError(m, e)

        return data


def mkcallargs(**kw):
    return kw


versiontag_pattern = re_compile('[^a-zA-Z0-9_-]')

def mk_versiontag(version):
    if not version or version == 'v':
        return ''

    return '_' + re_sub(versiontag_pattern, '_', version)


def get_callpoint(pointname, version=None, automake=None, **kw):

    versiontag = mk_versiontag(version)
    components = pointname.split('.')

    appname = components[0]
    if len(components) < 2:
        raise ValueError("invalid pointname '%s'" % (pointname,))

    category = components[1]
    if not category or category not in ['clients', 'servers']:
        raise ValueError("invalid pointname '%s'" % (pointname,))

    modname = ('%s.callpoint.API_Callpoint%s' 
                                            % (pointname, versiontag))

    try:
        API_Callpoint = imp_module(modname)
        return API_Callpoint
    except ImportError:
        if not automake:
            raise

    if category != 'clients':
        m = ("Can only auto-make callpoint in 'clients' not '%s'" % (category,))
        raise ValueError(m)

    components = components[1:]
    if not components:
        raise ValueError("invalid pointname '%s'" % (pointname))

    pointname = '.'.join(components)
    if pointname == 'quotaholder':
        apiname = 'quotaholder.api.QuotaholderAPI'
    else:
        apiname = '%s.api.API_Spec%s' % (pointname, versiontag)

    API_Spec = imp_module(apiname)

    basename = 'commissioning.clients.%s.API_Callpoint' % (automake,)
    BaseCallpoint = imp_module(basename)

    stupidpython = (appname,
                    version if version is not None else 'v',
                    pointname,
                    automake)

    class AutoCallpoint(BaseCallpoint):
        appname, version, pointname, automake = stupidpython
        api_spec = API_Spec()

    return AutoCallpoint

