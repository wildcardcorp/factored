import time
import struct
import hmac
import hashlib
import base64
from factored.models import DBSession, User
from pyramid.httpexceptions import HTTPFound


_auth_plugins = []


class FactoredPlugin(object):

    def __init__(self, name, path, view, view_config):
        self.name = name
        self.path = path
        self.view = view
        self.view_config = view_config


def addFactoredPlugin(name, path, view, view_config):
    _auth_plugins.append(FactoredPlugin(name, path, view, view_config))


def getFactoredPlugins():
    return _auth_plugins


def authenticate(secretkey, code_attempt):
    tm = int(time.time() / 30)

    secretkey = base64.b32decode(secretkey)

    # try 30 seconds behind and ahead as well
    for ix in [-1, 0, 1]:
        # convert timestamp to raw bytes
        b = struct.pack(">q", tm + ix)

        # generate HMAC-SHA1 from timestamp based on secret key
        hm = hmac.HMAC(secretkey, b, hashlib.sha1).digest()

        # extract 4 bytes from digest based on LSB
        offset = ord(hm[-1]) & 0x0F
        truncatedHash = hm[offset:offset + 4]

        # get the code from it
        code = struct.unpack(">L", truncatedHash)[0]
        code &= 0x7FFFFFFF
        code %= 1000000

        if ("%06d" % code) == str(code_attempt):
            return True

    return False


def google_auth_view(req):
    if req.method == "POST":
        name = req.params.get('username')
        code = req.params.get('code')
        user = DBSession.query(User).filter_by(username=name).all()
        if len(user) > 0:
            user = user[0]
            if authenticate(user.secret, code):
                creds = {}
                creds['repoze.who.userid'] = name
                creds['identifier'] = req.environ['auth_tkt']
                who_api = req.environ['who_api']
                headers = who_api.remember(creds)
                raise HTTPFound(location='/', headers=headers)
    return {'username': req.params.get('username', '')}


addFactoredPlugin('Google Auth', 'ga', google_auth_view,
    dict(route_name='Google Auth', renderer='templates/googleauth.pt'))
