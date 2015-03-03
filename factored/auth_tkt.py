from webob.request import BaseRequest as Request
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authentication import AuthTktCookieHelper
try:
    from pyramid.authentication import EXPIRE
except ImportError:
    EXPIRE = object()
import datetime

_marker = object()


class CookieHelper(AuthTktCookieHelper):
    def __init__(self, *args, **kwargs):
        self.cookie_domain = kwargs.pop('cookie_domain', False)
        super(CookieHelper, self).__init__(*args, **kwargs)

    def _get_cookies(self, environ, value, max_age=None):
        cookies = super(CookieHelper, self)._get_cookies(environ, value,
                                                         max_age)
        if self.cookie_domain:
            if max_age is EXPIRE:
                max_age = "; Max-Age=0; Expires=Wed, 31-Dec-97 23:59:59 GMT"
            elif max_age is not None:
                later = datetime.datetime.utcnow() + datetime.timedelta(
                    seconds=int(max_age))
                # Wdy, DD-Mon-YY HH:MM:SS GMT
                expires = later.strftime('%a, %d %b %Y %H:%M:%S GMT')
                # the Expires header is *required* at least for IE7 (IE7 does
                # not respect Max-Age)
                max_age = "; Max-Age=%s; Expires=%s" % (max_age, expires)
            else:
                max_age = ''

            cookies.append(('Set-Cookie', '%s="%s"; Path=%s; Domain=%s%s%s' % (
                self.cookie_name, value, self.path,
                self.cookie_domain, max_age, self.static_flags)))
        return cookies


class AuthenticationPolicy(AuthTktAuthenticationPolicy):
    def __init__(self, secret, callback=None, cookie_name='auth_tkt',
                 secure=False, include_ip=False, timeout=None,
                 reissue_time=None, max_age=None, path="/", http_only=False,
                 wild_domain=True, cookie_domain=False, debug=False,
                 hashalg='sha512'):
        self.cookie = CookieHelper(
            secret,
            cookie_name=cookie_name,
            secure=secure,
            include_ip=include_ip,
            timeout=timeout,
            reissue_time=reissue_time,
            max_age=max_age,
            http_only=http_only,
            path=path,
            wild_domain=wild_domain,
            cookie_domain=cookie_domain,
            hashalg=hashalg)
        self.callback = callback
        self.debug = debug


class AuthTktAuthenticator(object):

    def __init__(self, policy, environ):
        self.policy = policy
        self.environ = environ
        self.request = Request(environ)

    def remember(self, principal, **kw):
        return self.policy.remember(self.request, principal, **kw)

    def authenticate(self):
        identity = self.policy.unauthenticated_userid(self.request)
        if identity:
            self.environ['factored.identity'] = identity
            # set the REMOTE_USER
            self.environ['REMOTE_USER'] = identity
            # also set a header for username
            self.environ['HTTP_FACTORED_USER'] = identity
            return identity
