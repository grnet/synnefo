from pyramid.configuration import Configurator

def main(global_config, **settings):
    """ This function returns our WSGI application.
    """
    config = Configurator(settings=settings)
    config.add_static_view('static', 'synnefo:static')
    config.add_route('home', '/', 
                     view='synnefo.views.home',
                     view_renderer='templates/home.pt')

    config.add_route('instances', '/instances', 
                     view='synnefo.views.instances',
                     view_renderer='templates/instances.pt')

    config.add_route('storage', '/storage', 
                     view='synnefo.views.storage',
                     view_renderer='templates/storage.pt')

    config.add_route('images', '/images', 
                     view='synnefo.views.images',
                     view_renderer='templates/images.pt')

    config.add_route('networks', '/network', 
                     view='synnefo.views.network',
                     view_renderer='templates/network.pt')
    return config.make_wsgi_app()

