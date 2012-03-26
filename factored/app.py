from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from wsgiproxy.exactproxy import proxy_exact_request
from repoze.who.plugins.auth_tkt import make_plugin
from repoze.who.api import APIFactory
from repoze.who.classifiers import default_request_classifier
from repoze.who.classifiers import default_challenge_decider
from pyramid.httpexceptions import HTTPFound
from factored.models import DBSession
from factored.auth import getFactoredPlugins, getFactoredPlugin
from factored.finders import getUserFinderPlugin
import os
from pyramid_mailer.mailer import Mailer
from factored.utils import get_context


def notfound(req):
    return HTTPFound(location=req.registry['settings']['base_auth_url'])


def _tolist(val):
    lines = val.splitlines()
    return [l.strip() for l in lines if l.strip()]


def auth_chooser(req):
    auth_types = []
    settings = req.registry['settings']
    base_path = settings['base_auth_url']
    supported_types = settings['supported_auth_schemes']
    if len(supported_types) == 1:
        plugin = getFactoredPlugin(supported_types[0])
        raise HTTPFound(location="%s/%s" % (base_path, plugin.path))
    for plugin in getFactoredPlugins():
        if plugin.name in supported_types:
            auth_types.append({
                'name': plugin.name,
                'url': os.path.join(base_path, plugin.path)
                })
    return get_context(req, auth_types=auth_types)


def get_settings(config, prefix):
    settings = {}
    for key, val in config.items():
        if key.startswith(prefix):
            settings[key[len(prefix):]] = val
    return settings


class Authenticator(object):

    def __init__(self, app, global_config, base_auth_url='/auth',
                    supported_auth_schemes="Google Auth",
                    email_auth_window='120', allowgooglecodereminder='false',
                    **settings):
        self.app = app
        self.supported_auth_schemes = _tolist(supported_auth_schemes)
        self.base_auth_url = base_auth_url
        self.email_auth_window = int(email_auth_window)

        self.auth_tkt = make_plugin(**get_settings(settings, 'auth_tkt.'))
        self.email_auth_settings = get_settings(settings, 'email_auth.')
        self.allowgooglecodereminder = \
            allowgooglecodereminder.lower() == 'true' or False
        self.allowgooglecodereminder_settings = get_settings(settings,
            'allowgooglecodereminder.')

        self.who = APIFactory([('auth_tkt', self.auth_tkt)],
            [('auth_tkt', self.auth_tkt)], [], [],
            default_request_classifier, default_challenge_decider)

        # db configuration
        engine = engine_from_config(settings, 'sqlalchemy.')
        DBSession.configure(bind=engine)

        finder_name = settings.get('autouserfinder', None)
        if finder_name:
            plugin = getUserFinderPlugin(finder_name)
            if plugin:
                self.userfinder = plugin(**get_settings(settings,
                    'autouserfinder.'))
            else:
                raise Exception('User finder not found: %s', finder_name)

        config = Configurator(settings=settings)
        for plugin in getFactoredPlugins():
            config.add_route(plugin.name, os.path.join(base_auth_url,
                                                       plugin.path))
            config.add_view(plugin, route_name=plugin.name,
                                    renderer=plugin.renderer)
        config.add_route('auth', base_auth_url)
        config.add_view(auth_chooser, route_name='auth',
            renderer='templates/auth-chooser.pt')

        self.static_path = os.path.join(base_auth_url, 'authstatic')
        config.add_static_view(name=self.static_path,
                               path='factored:static')
        config.add_notfound_view(notfound, append_slash=True)

        # add some things to registry
        config.registry['mailer'] = Mailer.from_settings(settings)
        config.registry['settings'] = self.__dict__
        self.pyramid = config.make_wsgi_app()

    def __call__(self, environ, start_response):
        who_api = self.who(environ)
        environ['who_api'] = who_api
        if who_api.authenticate():
            return self.app(environ, start_response)
        else:
            return self.pyramid(environ, start_response)


class SimpleProxy(object):

    def __init__(self, global_config, server, port):
        self.server = server
        self.port = port

    def __call__(self, environ, start_response):
        environ['SERVER_NAME'] = self.server
        environ['SERVER_PORT'] = self.port
        return proxy_exact_request(environ, start_response)
