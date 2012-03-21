from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from wsgiproxy.exactproxy import proxy_exact_request
from repoze.who.plugins.auth_tkt import make_plugin
from repoze.who.api import APIFactory
from repoze.who.classifiers import default_request_classifier
from repoze.who.classifiers import default_challenge_decider
from pyramid.httpexceptions import HTTPFound
from factored.models import DBSession
from factored.auth import getFactoredPlugins
import os


def notfound(req):
    return HTTPFound(location=req.environ['settings']['base_auth_url'])


def _tolist(val):
    lines = val.splitlines()
    return [l.strip() for l in lines]


def auth_chooser(req):
    auth_types = []
    settings = req.environ['settings']
    supported_types = settings['supported_auth_schemes']
    for plugin in getFactoredPlugins():
        if plugin.name in supported_types:
            auth_types.append({
                'name': plugin.name,
                'url': os.path.join(settings['base_auth_url'], plugin.path)
                })
    return {'auth_types': auth_types}


class Authenticator(object):

    def __init__(self, global_config, server, port, auth_secret,
                    auth_cookie_name="auth", base_auth_url='/auth',
                    auth_secure=False, auth_include_ip=False,
                    auth_timeout=12345, auth_reissue_time=1234,
                    supported_auth_schemes="Google Auth",
                    **settings):
        self.server = server
        self.port = port
        self.supported_auth_schemes = _tolist(supported_auth_schemes)
        self.base_auth_url = base_auth_url

        self.auth_tkt = make_plugin(
            secret=auth_secret, cookie_name=auth_cookie_name,
            secure=auth_secure, include_ip=auth_include_ip,
            timeout=auth_timeout, reissue_time=auth_reissue_time)

        self.who = APIFactory([('auth_tkt', self.auth_tkt)],
            [('auth_tkt', self.auth_tkt)], [], [],
            default_request_classifier, default_challenge_decider)
        engine = engine_from_config(settings, 'sqlalchemy.')
        DBSession.configure(bind=engine)
        config = Configurator(settings=settings)
        for plugin in getFactoredPlugins():
            config.add_route(plugin.name, os.path.join(base_auth_url,
                                                       plugin.path))
            config.add_view(plugin.view, **plugin.view_config)
        config.add_route('auth', base_auth_url)
        config.add_view(auth_chooser, route_name='auth',
            renderer='templates/auth.pt')

        config.add_static_view(name='authstatic', path='factored:static')
        config.add_notfound_view(notfound, append_slash=True)
        self.pyramid = config.make_wsgi_app()

    def proxy(self, environ, start_response):
        environ['SERVER_NAME'] = self.server
        environ['SERVER_PORT'] = self.port
        return proxy_exact_request(environ, start_response)

    def __call__(self, environ, start_response):
        environ['settings'] = self.__dict__
        who_api = self.who(environ)
        environ['who_api'] = who_api
        if who_api.authenticate():
            return self.proxy(environ, start_response)
        else:
            return self.pyramid(environ, start_response)
