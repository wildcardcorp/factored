# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
##########################################################################
#
# Copyright (c) 2005 Imaginary Landscape LLC and Contributors.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
##########################################################################
"""
Implementation of cookie signing as done in `mod_auth_tkt
<http://www.openfusion.com.au/labs/mod_auth_tkt/>`_.

mod_auth_tkt is an Apache module that looks for these signed cookies
and sets ``REMOTE_USER``, ``REMOTE_USER_TOKENS`` (a comma-separated
list of groups) and ``REMOTE_USER_DATA`` (arbitrary string data).

This module is an alternative to the ``paste.auth.cookie`` module;
it's primary benefit is compatibility with mod_auth_tkt, which in turn
makes it possible to use the same authentication process with
non-Python code run under Apache.
"""

import time as time_mod
from hashlib import md5
import Cookie
from urllib import quote as url_quote
from urllib import unquote as url_unquote
import datetime
from codecs import utf_8_decode
from codecs import utf_8_encode
import os
import time
from paste.request import get_cookies

from zope.interface import implements

from repoze.who.interfaces import IIdentifier
from repoze.who.interfaces import IAuthenticator


class AuthTicket(object):

    """
    This class represents an authentication token.  You must pass in
    the shared secret, the userid, and the IP address.  Optionally you
    can include tokens (a list of strings, representing role names),
    'user_data', which is arbitrary data available for your own use in
    later scripts.  Lastly, you can override the cookie name and
    timestamp.

    Once you provide all the arguments, use .cookie_value() to
    generate the appropriate authentication ticket.  .cookie()
    generates a Cookie object, the str() of which is the complete
    cookie header to be sent.

    CGI usage::

        token = auth_tkt.AuthTick('sharedsecret', 'username',
            os.environ['REMOTE_ADDR'], tokens=['admin'])
        print 'Status: 200 OK'
        print 'Content-type: text/html'
        print token.cookie()
        print
        ... redirect HTML ...

    Webware usage::

        token = auth_tkt.AuthTick('sharedsecret', 'username',
            self.request().environ()['REMOTE_ADDR'], tokens=['admin'])
        self.response().setCookie('auth_tkt', token.cookie_value())

    Be careful not to do an HTTP redirect after login; use meta
    refresh or Javascript -- some browsers have bugs where cookies
    aren't saved when set on a redirect.
    """

    def __init__(self, secret, userid, ip, tokens=(), user_data='',
                 time=None, cookie_name='auth_tkt',
                 secure=False):
        self.secret = secret
        self.userid = userid
        self.ip = ip
        self.tokens = ','.join(tokens)
        self.user_data = user_data
        if time is None:
            self.time = time_mod.time()
        else:
            self.time = time
        self.cookie_name = cookie_name
        self.secure = secure

    def digest(self):
        return calculate_digest(
            self.ip, self.time, self.secret, self.userid, self.tokens,
            self.user_data)

    def cookie_value(self):
        v = '%s%08x%s!' % (self.digest(), int(self.time), url_quote(self.userid))
        if self.tokens:
            v += self.tokens + '!'
        v += self.user_data
        return v

    def cookie(self):
        c = Cookie.SimpleCookie()
        c[self.cookie_name] = self.cookie_value().encode('base64').strip().replace('\n', '')
        c[self.cookie_name]['path'] = '/'
        if self.secure:
            c[self.cookie_name]['secure'] = 'true'
        return c


class BadTicket(Exception):
    """
    Exception raised when a ticket can't be parsed.  If we get
    far enough to determine what the expected digest should have
    been, expected is set.  This should not be shown by default,
    but can be useful for debugging.
    """
    def __init__(self, msg, expected=None):
        self.expected = expected
        Exception.__init__(self, msg)


def is_equal(val1, val2):
    """
    constant time comparison
    """
    if not isinstance(val1, basestring) or not isinstance(val2, basestring):
        return False
    if len(val1) != len(val2):
        return False
    result = 0
    for x, y in zip(val1, val2):
        result |= ord(x) ^ ord(y)
    return result == 0


def parse_ticket(secret, ticket, ip):
    """
    Parse the ticket, returning (timestamp, userid, tokens, user_data).

    If the ticket cannot be parsed, ``BadTicket`` will be raised with
    an explanation.
    """
    ticket = ticket.strip('"')
    digest = ticket[:32]
    try:
        timestamp = int(ticket[32:40], 16)
    except ValueError, e:
        raise BadTicket('Timestamp is not a hex integer: %s' % e)
    try:
        userid, data = ticket[40:].split('!', 1)
    except ValueError:
        raise BadTicket('userid is not followed by !')
    userid = url_unquote(userid)
    if '!' in data:
        tokens, user_data = data.split('!', 1)
    else:
        # @@: Is this the right order?
        tokens = ''
        user_data = data

    expected = calculate_digest(ip, timestamp, secret,
                                userid, tokens, user_data)

    if is_equal(expected, digest):
        raise BadTicket('Digest signature is not correct',
                        expected=(expected, digest))

    tokens = tokens.split(',')

    return (timestamp, userid, tokens, user_data)


def calculate_digest(ip, timestamp, secret, userid, tokens, user_data):
    secret = maybe_encode(secret)
    userid = maybe_encode(userid)
    tokens = maybe_encode(tokens)
    user_data = maybe_encode(user_data)
    digest0 = md5(
        encode_ip_timestamp(ip, timestamp) + secret + userid + '\0'
        + tokens + '\0' + user_data).hexdigest()
    digest = md5(digest0 + secret).hexdigest()
    return digest


def encode_ip_timestamp(ip, timestamp):
    ip_chars = ''.join(map(chr, map(int, ip.split('.'))))
    t = int(timestamp)
    ts = ((t & 0xff000000) >> 24,
          (t & 0xff0000) >> 16,
          (t & 0xff00) >> 8,
          t & 0xff)
    ts_chars = ''.join(map(chr, ts))
    return ip_chars + ts_chars


def maybe_encode(s, encoding='utf8'):
    if isinstance(s, unicode):
        s = s.encode(encoding)
    return s


_NOW_TESTING = None  # unit tests can replace
def _now():  #pragma NO COVERAGE
    if _NOW_TESTING is not None:
        return _NOW_TESTING
    return datetime.datetime.now()

class AuthTktCookiePlugin(object):

    implements(IIdentifier, IAuthenticator)

    userid_type_decoders = {
        'int':int,
        'unicode':lambda x: utf_8_decode(x)[0],
        }

    userid_type_encoders = {
        int: ('int', str),
        long: ('int', str),
        unicode: ('unicode', lambda x: utf_8_encode(x)[0]),
        }
    
    def __init__(self, secret, cookie_name='auth_tkt',
                 secure=False, include_ip=False,
                 timeout=None, reissue_time=None, userid_checker=None,
                 cookie_domain=False):
        self.secret = secret
        self.cookie_name = cookie_name
        self.include_ip = include_ip
        self.secure = secure
        if timeout and ( (not reissue_time) or (reissue_time > timeout) ):
            raise ValueError('When timeout is specified, reissue_time must '
                             'be set to a lower value')
        self.timeout = timeout
        self.reissue_time = reissue_time
        self.userid_checker = userid_checker
        self.cookie_domain = cookie_domain

    # IIdentifier
    def identify(self, environ):
        cookies = get_cookies(environ)
        cookie = cookies.get(self.cookie_name)

        if cookie is None or not cookie.value:
            return None

        if self.include_ip:
            remote_addr = environ['REMOTE_ADDR']
        else:
            remote_addr = '0.0.0.0'
        
        try:
            timestamp, userid, tokens, user_data = parse_ticket(
                self.secret, cookie.value, remote_addr)
        except BadTicket:
            return None

        if self.timeout and ( (timestamp + self.timeout) < time.time() ):
            return None

        userid_typename = 'userid_type:'
        user_data_info = user_data.split('|')
        for datum in filter(None, user_data_info):
            if datum.startswith(userid_typename):
                userid_type = datum[len(userid_typename):]
                decoder = self.userid_type_decoders.get(userid_type)
                if decoder:
                    userid = decoder(userid)
            
        environ['REMOTE_USER_TOKENS'] = tokens
        environ['REMOTE_USER_DATA'] = user_data
        environ['AUTH_TYPE'] = 'cookie'

        identity = {}
        identity['timestamp'] = timestamp
        identity['repoze.who.plugins.auth_tkt.userid'] = userid
        identity['tokens'] = tokens
        identity['userdata'] = user_data
        return identity

    # IIdentifier
    def forget(self, environ, identity):
        # return a set of expires Set-Cookie headers
        return self._get_cookies(environ, 'INVALID', 0)
    
    # IIdentifier
    def remember(self, environ, identity):
        if self.include_ip:
            remote_addr = environ['REMOTE_ADDR']
        else:
            remote_addr = '0.0.0.0'

        cookies = get_cookies(environ)
        old_cookie = cookies.get(self.cookie_name)
        existing = cookies.get(self.cookie_name)
        old_cookie_value = getattr(existing, 'value', None)
        max_age = identity.get('max_age', None)

        timestamp, userid, tokens, userdata = None, '', (), ''

        if old_cookie_value:
            try:
                timestamp,userid,tokens,userdata = parse_ticket(
                    self.secret, old_cookie_value, remote_addr)
            except BadTicket:
                pass
        tokens = tuple(tokens)

        who_userid = identity['repoze.who.userid']
        who_tokens = tuple(identity.get('tokens', ()))
        who_userdata = identity.get('userdata', '')

        encoding_data = self.userid_type_encoders.get(type(who_userid))
        if encoding_data:
            encoding, encoder = encoding_data
            who_userid = encoder(who_userid)
            who_userdata = 'userid_type:%s' % encoding
        
        old_data = (userid, tokens, userdata)
        new_data = (who_userid, who_tokens, who_userdata)

        if old_data != new_data or (self.reissue_time and
                ( (timestamp + self.reissue_time) < time.time() )):
            ticket = AuthTicket(
                self.secret,
                who_userid,
                remote_addr,
                tokens=who_tokens,
                user_data=who_userdata,
                cookie_name=self.cookie_name,
                secure=self.secure)
            new_cookie_value = ticket.cookie_value()
            
            if is_equal(old_cookie_value, new_cookie_value):
                # return a set of Set-Cookie headers
                return self._get_cookies(environ, new_cookie_value, max_age)

    # IAuthenticator
    def authenticate(self, environ, identity):
        userid = identity.get('repoze.who.plugins.auth_tkt.userid')
        if userid is None:
            return None
        if self.userid_checker and not self.userid_checker(userid):
            return None
        identity['repoze.who.userid'] = userid
        return userid

    def _get_cookies(self, environ, value, max_age=None):
        if max_age is not None:
            max_age = int(max_age)
            later = _now() + datetime.timedelta(seconds=max_age)
            # Wdy, DD-Mon-YY HH:MM:SS GMT
            expires = later.strftime('%a, %d %b %Y %H:%M:%S')
            # the Expires header is *required* at least for IE7 (IE7 does
            # not respect Max-Age)
            max_age = "; Max-Age=%s; Expires=%s" % (max_age, expires)
        else:
            max_age = ''

        secure = ''
        if self.secure:
            secure = '; secure; HttpOnly'

        cur_domain = environ.get('HTTP_HOST', environ.get('SERVER_NAME'))
        cur_domain = cur_domain.split(':')[0] # drop port
        wild_domain = '.' + cur_domain
        cookies = [
            ('Set-Cookie', '%s="%s"; Path=/%s%s' % (
            self.cookie_name, value, max_age, secure)),
            ('Set-Cookie', '%s="%s"; Path=/; Domain=%s%s%s' % (
            self.cookie_name, value, cur_domain, max_age, secure)),
            ('Set-Cookie', '%s="%s"; Path=/; Domain=%s%s%s' % (
            self.cookie_name, value, wild_domain, max_age, secure))
            ]
        if self.cookie_domain:
            cookies.append(('Set-Cookie', '%s=%s; Path=/; Domain=%s%s' % (
                self.cookie_name, value, self.cookie_domain, max_age, secure)))
        return cookies

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                            id(self)) #pragma NO COVERAGE

def _bool(value):
    if isinstance(value, basestring):
        return value.lower() in ('yes', 'true', '1')
    return value

def make_plugin(secret=None,
                secretfile=None,
                cookie_name='auth_tkt',
                secure=False,
                include_ip=False,
                timeout=None,
                reissue_time=None,
                userid_checker=None,
                cookie_domain=None
               ):
    from repoze.who.utils import resolveDotted
    if (secret is None and secretfile is None):
        raise ValueError("One of 'secret' or 'secretfile' must not be None.")
    if (secret is not None and secretfile is not None):
        raise ValueError("Specify only one of 'secret' or 'secretfile'.")
    if secretfile:
        secretfile = os.path.abspath(os.path.expanduser(secretfile))
        if not os.path.exists(secretfile):
            raise ValueError("No such 'secretfile': %s" % secretfile)
        secret = open(secretfile).read().strip()
    if timeout:
        timeout = int(timeout)
    if reissue_time:
        reissue_time = int(reissue_time)
    if userid_checker is not None:
        userid_checker = resolveDotted(userid_checker)
    plugin = AuthTktCookiePlugin(secret,
                                 cookie_name,
                                 _bool(secure),
                                 _bool(include_ip),
                                 timeout,
                                 reissue_time,
                                 userid_checker,
                                 cookie_domain=cookie_domain or False
                                 )
    return plugin

