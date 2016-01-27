import base64
from datetime import datetime
from hashlib import sha256 as sha
import hashlib
import hmac
import struct
import time

from pyramid.threadlocal import get_current_registry

try:
    from urllib import urlencode
except:
    from urllib.parse import urlencode

import random
try:
    random = random.SystemRandom()
    using_sysrandom = True
except NotImplementedError:
    using_sysrandom = False


# generated when process started, hard to guess
SECRET = random.randint(0, 1000000)


def get_random_string(length=12,
                      allowed_chars='abcdefghijklmnopqrstuvwxyz'
                                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    """
    Returns a securely generated random string.

    The default length of 12 with the a-z, A-Z, 0-9 character set returns
    a 71-bit value. log_2((26+26+10)^12) =~ 71 bits
    """
    if not using_sysrandom:
        # This is ugly, and a hack, but it makes things better than
        # the alternative of predictability. This re-seeds the PRNG
        # using a value that is hard for an attacker to predict, every
        # time a random string is required. This may change the
        # properties of the chosen random sequence slightly, but this
        # is better than absolute predictability.
        random.seed(
            sha(
                "%s%s%s" % (
                    random.getstate(),
                    time.time(),
                    SECRET)
                ).digest())
    return ''.join([random.choice(allowed_chars) for i in range(length)])


def generate_random_google_code(length=10):
    return base64.b32encode(get_random_string(length))


def make_random_code(length=255):
    prehash = hashlib.sha1(str(get_random_string(length)).encode('utf-8')).hexdigest()[:5]
    return hashlib.sha1(
        (prehash + str(datetime.now().microsecond)).encode('utf-8')).hexdigest()[:length]


def get_barcode_image(username, secretkey, appname):
    url = "https://www.google.com/chart"
    url += "?chs=200x200&chld=M|0&cht=qr&chl=otpauth://totp/"
    username = username + '--' + appname
    url += username + "%3Fsecret%3D" + secretkey
    return url


def get_google_auth_code(secretkey, tm=None):
    if tm is None:
        tm = int(time.time() / 30)
    secretkey = base64.b32decode(secretkey)
    # convert timestamp to raw bytes
    b = struct.pack(">q", tm)

    # generate HMAC-SHA1 from timestamp based on secret key
    hm = hmac.HMAC(secretkey, b, hashlib.sha1).digest()

    # extract 4 bytes from digest based on LSB
    offset = ord(hm[-1]) & 0x0F
    truncatedHash = hm[offset:offset + 4]

    # get the code from it
    code = struct.unpack(">L", truncatedHash)[0]
    code &= 0x7FFFFFFF
    code %= 1000000
    return "%06d" % code


def create_user(username, session=None):
    from factored.models import DBSession, User
    if session is None:
        session = DBSession()
    secret = generate_random_google_code()
    user = User(username=username, secret=secret)
    session.add(user)
    return user


NO_VALUE = object()


class CombinedDict(object):
    def __init__(self, *args):
        self.dicts = args

    def __getattr__(self, name, default=NO_VALUE):
        try:
            return self[name]
        except KeyError:
            if NO_VALUE == default:
                raise AttributeError(name)
            return default

    def __getitem__(self, name):
        """
        need to handle nested dictionaries also
        """
        founddicts = []
        for dic in self.dicts:
            if name in dic:
                val = dic[name]
                if type(val) == dict:
                    founddicts.append(val)
                else:
                    return val
        if founddicts:
            return CombinedDict(*founddicts)
        raise KeyError(name)


class FakeMailer(object):

    def __init__(self, req):
        self.req = req
        self.messages = []

    def send_immediately(self, message):
        self.messages.append(message)
        print("""To: %s
From: %s
Subject: %s
Body: %s""" % (
            ','.join(message.recipients),
            message.sender,
            message.subject,
            message.body
        ))

    send = send_immediately


FAKE_MAILER_KEY = 'fakemailer'


def get_mailer(req):
    settings = req.registry.settings
    if settings.get('mail.host', '') == 'debug':
        if FAKE_MAILER_KEY not in req.environ:
            req.environ[FAKE_MAILER_KEY] = FakeMailer(req)
        return req.environ[FAKE_MAILER_KEY]
    return req.registry['mailer']


def generate_url(req, path, params={}):
    scheme = None
    if 'X-Forwarded-Protocol' in req.headers:
        scheme = req.headers['X-Forwarded-Protocol']
    elif 'wsgi.url_scheme' in req.environ:
        scheme = req.environ['wsgi.url_scheme']
    elif req.url.startswith('https://'):
        scheme = 'https'
    if scheme is None:
        # look for HTTP_ORIGIN
        if 'HTTP_ORIGIN' in req.environ:
            host = req.environ['HTTP_ORIGIN']
        else:
            host = ''
    else:
        host = '%s://%s' % (scheme, req.environ['HTTP_HOST'])
    url = '%s%s' % (host, path)
    if params:
        url += '?' + urlencode(params)
    return url


def create_message_id(_id=''):
    registry = get_current_registry()
    domain = 'localhost'
    if registry:
        domain = registry.settings.get('mail.domain', domain)
    if not _id:
        _id = '%s-%s' % (
            str(time.time()),
            get_random_string(20))
    return '<%s@%s>' % (_id, domain)