import time
import struct
import hmac
import hashlib
import base64
from factored.models import DBSession, User
from pyramid.httpexceptions import HTTPFound
from pyramid_simpleform import Form
from formencode import Schema, validators
from pyramid_simpleform.renderers import FormRenderer

_auth_plugins = []


class BaseSchema(Schema):
    filter_extra_fields = True
    allow_extra_fields = True


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


class GoogleAuthSchema(Schema):

    username = validators.MinLength(5, not_empty=True)
    code = validators.Int(not_empty=True)


class GoogleAuthForm(Form):

    def authenticate(self, secretkey, code_attempt):
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
    form = GoogleAuthForm(req, schema=GoogleAuthSchema)
    if req.method == "POST":
        if form.validate():
            user = DBSession.query(User).filter_by(
                username=form.data['username']).first()
            if user is None:
                form.errors['username'] = u'Invalid username'
            elif form.authenticate(user.secret, form.data['code']):
                creds = {}
                creds['repoze.who.userid'] = form.data['username']
                creds['identifier'] = req.environ['settings']['auth_tkt']
                who_api = req.environ['who_api']
                headers = who_api.remember(creds)
                raise HTTPFound(location='/', headers=headers)
            else:
                form.errors['code'] = u'Code did not validate'
                form.data['code'] = u''

    return {'form': FormRenderer(form)}


addFactoredPlugin('Google Auth', 'ga', google_auth_view,
    dict(route_name='Google Auth', renderer='templates/googleauth.pt'))
