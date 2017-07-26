from pyramid.config import Configurator
from factored.auth_tkt import AuthTktAuthenticator, AuthenticationPolicy
from factored.finders import getUserFinderPlugin
from factored import TEMPLATE_CUSTOMIZATIONS
import os
from pyramid_mailer.mailer import Mailer
from factored import subscribers
subscribers  # pyflakes
from factored.request import Request
from factored.sm import SMFilter

from pkg_resources import iter_entry_points


def _tolist(val):
    if type(val) == list:
        return val
    lines = val.splitlines()
    return [l.strip() for l in lines if l.strip()]


def get_settings(config, prefix):
    settings = {}
    for key, val in config.items():
        if key.startswith(prefix):
            settings[key[len(prefix):]] = val
    return settings


def nested_settings(settings):
    newsettings = {}
    for key, val in settings.items():
        parts = key.split('.')
        loc = newsettings
        for part in parts[:-1]:
            if part not in loc:
                loc[part] = {}
            loc = loc[part]
        loc[parts[-1]] = val
    return newsettings


def normalize_settings(settings):
    for key, val in settings.items():
        if val in ('true', 'True', 't'):
            settings[key] = True
        elif val in ('false', 'False', 'f'):
            settings[key] = False
    return settings


db_factories = dict([(i.name, i.load()) for i in iter_entry_points(
                     group='factored.db_factory', name=None)])


class Authenticator(object):

    def __init__(self, *args, **settings):
        if len(args) == 1:
            # regular app
            app = None
        else:
            app = args[0]
        self.initialize_settings(app, settings)

        # db configuration
        db_factory_name = settings.get('db_factory_name', 'sql')
        if db_factory_name not in db_factories:
            raise Exception("Invalid db_factory_name: %s" % db_factory_name)
        settings['db_session_id'], self.db = db_factories[db_factory_name](settings, self)  # noqa

        self.setup_autouserfinder(settings)

        # start pyramid application configuration
        config = Configurator(settings=settings, request_factory=Request)
        try:
            import pyramid_chameleon  # noqa
            config.include('pyramid_chameleon')
        except ImportError:
            pass

        self.setup_plugins(config, settings)

        from factored.views import auth_chooser, notfound
        config.add_route('auth', self.base_auth_url)
        config.add_view(auth_chooser, route_name='auth',
                        renderer='templates/layout.pt')

        # setup template customization registration
        if TEMPLATE_CUSTOMIZATIONS not in config.registry:
            config.registry[TEMPLATE_CUSTOMIZATIONS] = {}

        # static paths for resources
        self.static_path = os.path.join(self.base_auth_url, 'authstatic')
        config.add_static_view(name=self.static_path,
                               path='factored:static')
        config.add_notfound_view(notfound, append_slash=True)

        # add some things to registry
        config.registry['mailer'] = Mailer.from_settings(settings)
        config.registry['settings'] = self.__dict__
        config.registry['formtext'] = nested_settings(
            get_settings(settings, 'formtext.'))
        config.registry['app'] = self

        config.scan()
        self.config = config
        self.registry = self.config.registry
        try:
            self.app.config.registry['factored'] = self
        except:
            pass
        self.pyramid = config.make_wsgi_app()

    def setup_plugins(self, config, settings):
        from factored.plugins import getFactoredPlugins
        from factored.views import AuthView
        for plugin in getFactoredPlugins():
            setattr(
                self, '%s_settings' % plugin.path,
                nested_settings(get_settings(settings, '%s.' % plugin.path)))
            config.add_route(
                plugin.name,
                os.path.join(self.base_auth_url, plugin.path))
            config.add_view(AuthView, route_name=plugin.name,
                            renderer='templates/layout.pt')

    def setup_autouserfinder(self, settings):
        finder_name = settings.get('autouserfinder', None)
        if finder_name:
            plugin = getUserFinderPlugin(finder_name)
            if plugin:
                self.userfinder = plugin(
                    **get_settings(settings, 'autouserfinder.'))
            else:
                raise Exception('User finder not found: %s', finder_name)

    def initialize_settings(self, app, settings):
        self.app = app
        self.appname = settings.pop('appname', 'REPLACEME')
        self.supported_auth_schemes = _tolist(
            settings.pop('supported_auth_schemes', "Google Auth"))
        self.base_auth_url = settings.pop('base_auth_url', '/auth')
        self.email_auth_window = int(settings.pop('email_auth_window', '120'))
        self.auth_timeout = int(settings.pop('auth_timeout', '7200'))
        self.auth_remember_timeout = int(settings.pop(
            'auth_remember_timeout', '86400'))

        auth_settings = normalize_settings(get_settings(settings, 'auth_tkt.'))
        self.auth_tkt_policy = AuthenticationPolicy(**auth_settings)
        self.allowcodereminder = settings.pop(
            'allowcodereminder', 'false').lower() == 'true' or False
        self.allowcodereminder_settings = get_settings(
            settings, 'allowcodereminder.')

        settings['hide_banner'] = settings.get(
            'hide_banner', 'false').strip().lower() == 'true'
        self.hide_banner = settings['hide_banner']

        self.excepted_paths = [a.strip() for a in
            settings.get("excepted_paths", "").splitlines()]

    def __call__(self, environ, start_response):
        def wrapped_app(environ2, start_response2):
            auth = AuthTktAuthenticator(self.auth_tkt_policy, environ2)
            environ2['auth'] = auth
            path = environ2['PATH_INFO']
            excepted_paths = self.excepted_paths
            auth_result = auth.authenticate()
            if path in excepted_paths or auth_result:
                if self.app is not None:
                    # if this is a filter, we can pass on to the actual app
                    return self.app(environ2, start_response2)
            return self.pyramid(environ2, start_response2)
        return SMFilter(wrapped_app)(environ, start_response)


try:
    from wsgiproxy.exactproxy import proxy_exact_request

    class SimpleProxy(object):

        def __init__(self, global_config, server, port, urlscheme=None):
            self.server = server
            self.port = port
            self.scheme = urlscheme

        def __call__(self, environ, start_response):
            environ['SERVER_NAME'] = self.server
            environ['SERVER_PORT'] = self.port
            if self.scheme:
                environ['wsgi.url_scheme'] = self.scheme
            return proxy_exact_request(environ, start_response)
except ImportError:
    class SimpleProxy(object):
        def __init__(self, *args, **kwargs):
            raise Exception("Must install factored with [proxy] "
                            "requirement to use this.")
