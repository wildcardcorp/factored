import time
from factored.models import DBSession, User
from pyramid.httpexceptions import HTTPFound
from pyramid_simpleform import Form
from formencode import Schema, validators
from pyramid_simpleform.renderers import FormRenderer
from pyramid_mailer.message import Message
from factored.utils import make_random_code
from datetime import datetime
from datetime import timedelta
from factored.utils import get_google_auth_code
from factored.utils import get_context

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


def getFactoredPlugin(name):
    for plugin in _auth_plugins:
        if plugin.name == name:
            return plugin


def get_authorize_headers(req, username):
    creds = {}
    creds['repoze.who.userid'] = username
    creds['identifier'] = req.registry['settings']['auth_tkt']
    who_api = req.environ['who_api']
    return who_api.remember(creds)


class GoogleAuthSchema(BaseSchema):

    username = validators.MinLength(3, not_empty=True)
    code = validators.Int(not_empty=True)


class GoogleAuthForm(Form):

    def authenticate(self, secretkey, code_attempt):
        tm = int(time.time() / 30)
        # try 30 seconds behind and ahead as well
        for ix in [-1, 0, 1]:
            code = get_google_auth_code(secretkey, tm + ix)
            if code == str(code_attempt):
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
                headers = get_authorize_headers(req, form.data['username'])
                raise HTTPFound(location='/', headers=headers)
            else:
                form.errors['code'] = u'Code did not validate'
                form.data['code'] = u''

    return get_context(req, form=FormRenderer(form))


addFactoredPlugin('Google Auth', 'ga', google_auth_view,
    dict(route_name='Google Auth', renderer='templates/googleauth.pt'))


class EmailAuthSchema(BaseSchema):

    username = validators.Email(not_empty=True)


class EmailAuthCodeSchema(BaseSchema):
    username = validators.Email(not_empty=True)
    code = validators.MinLength(8, not_empty=True)


class EmailAuthForm(Form):
    pass


def email_auth_view(req):
    eform = EmailAuthForm(req, schema=EmailAuthSchema)
    cform = EmailAuthForm(req, schema=EmailAuthCodeSchema)
    send_submitted = validate_submitted = False
    if req.method == "POST":
        if req.POST.get('submit', '') == 'Send mail':
            if eform.validate():
                username = eform.data['username']
                user = DBSession.query(User).filter_by(
                    username=username).first()
                if user is None:
                    eform.errors['username'] = u'Invalid username'
                else:
                    send_submitted = True
                    cform.data['username'] = username
                    mailer = req.registry['mailer']
                    user.generated_code = make_random_code(12)
                    user.generated_code_time_stamp = datetime.utcnow()

                    message = req.registry['settings']['email_auth_settings']
                    message = message.copy()
                    message['recipients'] = [username]
                    message['body'] = message['body'].replace('{code}',
                        user.generated_code)
                    mailer.send(Message(**message))
        elif req.POST.get('submit', '') == 'Authenticate':
            validate_submitted = True
            if cform.validate():
                user = DBSession.query(User).filter_by(
                    username=cform.data['username']).first()
                if user is None:
                    cform.errors['code'] = u'Invalid username for this code'
                else:
                    window = req.registry['settings']['email_auth_window']
                    now = datetime.utcnow()
                    if cform.data['code'] == user.generated_code and \
                            now < (user.generated_code_time_stamp + \
                                        timedelta(seconds=window)):
                        headers = get_authorize_headers(req,
                            cform.data['username'])
                        raise HTTPFound(location='/', headers=headers)
                    else:
                        cform.errors['code'] = u'Code did not validate'
                        cform.data['code'] = u''
    return get_context(req, eform=FormRenderer(eform),
        cform=FormRenderer(cform), send_submitted=send_submitted,
        validate_submitted=validate_submitted)


addFactoredPlugin('Email', 'em', email_auth_view,
    dict(route_name="Email", renderer="templates/emailauth.pt"))
