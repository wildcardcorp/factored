from webob.cookies import RequestCookies


_marker = object()


class FakeRequest(object):
    """
    So we don't have to create webob request object if
    they're not logged in and the request just gets
    passed along
    """

    good_names = ('environ', 'cookies')

    def __init__(self, environ):
        self.environ = environ
        self.cookies = RequestCookies(environ)

    def __getattr__(self, name, default=_marker):
        if name in self.good_names:
            return self.__dict__[name]
        try:
            return self.environ[name]
        except KeyError:
            if default != _marker:
                return default
            raise AttributeError

    def __getitem__(self, name):
        return self.environ[name]


class AuthTktAuthenticator(object):

    def __init__(self, policy, environ):
        self.policy = policy
        self.environ = environ
        self.request = FakeRequest(environ)

    def remember(self, principal, **kw):
        return self.policy.remember(self.request, principal, **kw)

    def authenticate(self):
        identity = self.policy.unauthenticated_userid(self.request)
        if identity:
            self.environ['factored.identity'] = identity
            # set the REMOTE_USER
            self.environ['REMOTE_USER'] = identity
            return identity
