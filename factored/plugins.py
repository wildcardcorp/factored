import time
from factored.models import DBSession, User
from pyramid_simpleform import Form
from formencode import Schema, validators
from pyramid_mailer.message import Message
from factored.utils import make_random_code
from datetime import datetime
from datetime import timedelta
from factored.utils import get_google_auth_code
from factored.utils import create_user
from factored.utils import get_barcode_image
from pyramid.util import strings_differ
from copy import deepcopy as copy
import os

_auth_plugins = []


def nested_update(base, override):
    for key, val in override.items():
        baseval = base.get(key)
        if type(baseval) == dict:
            nested_update(baseval, val)
        else:
            base[key] = val
    return base


class BaseSchema(Schema):
    filter_extra_fields = True
    allow_extra_fields = True


def addFactoredPlugin(plugin):
    _auth_plugins.append(plugin)


def getFactoredPlugins():
    return _auth_plugins


def getFactoredPlugin(name):
    for plugin in _auth_plugins:
        if plugin.name == name:
            return plugin


def getPluginForRequest(req):
    app = req.registry['app']
    for plugin in getFactoredPlugins():
        pluginpath = os.path.join(app.base_auth_url, plugin.path)
        if pluginpath == req.path:
            return plugin(req)

class UsernameSchema(BaseSchema):
    username = validators.MinLength(3, not_empty=True)
    referrer = validators.UnicodeString(if_missing=u'')


class CodeSchema(BaseSchema):
    username = validators.MinLength(3, not_empty=True)
    code = validators.MinLength(4, not_empty=True)
    remember = validators.Bool()
    referrer = validators.UnicodeString(if_missing=u'')


class BasePlugin(object):
    name = None
    path = None
    username_schema = UsernameSchema
    code_schema = CodeSchema

    _formtext = {
        'title': None,
        'legend': None,
        'username': {
            'label': None,
            'desc': None
        },
        'code': {
            'label': u'Access Code',
            'desc': None
        },
        'button': {
            'username': u'Next',
            'authenticate': u'Authenticate',
            'codereminder': u'Send Code Reminder'
        },
        'error': {
            'invalid_username_code': u'Invalid username for this code',
            'invalid_code': u'Code did not validate',
            'invalid_username': u'Invalid username',
            'code_reminder': u'A code reminder email has been sent.'
        }
    }
    _formtext_overrides = {}

    def __init__(self, req):
        self.req = req
        self.uform = Form(req, schema=self.username_schema)
        self.cform = Form(req, schema=self.code_schema)
        self.formtext = nested_update(copy(self._formtext), self._formtext_overrides)

    def get_user(self, username):
        user = DBSession.query(User).filter_by(username=username).first()
        if user is None:
            if 'userfinder' in self.req.registry['settings']:
                finder = self.req.registry['settings']['userfinder']
                if finder(username):
                    return create_user(username)
        return user

    def check_code(self, user):
        return False

    def user_form_submitted_successfully(self, user):
        pass

    @property
    def allow_code_reminder(self):
        return False

    def send_code_reminder(self, user):
        pass


class GoogleAuthPlugin(BasePlugin):
    name = 'Google Auth'
    path = 'ga'

    _formtext_overrides = {
        'title': u'Google Authenticator',
        'legend': u'Use android app to authenticate...',
        'username': {
            'label': u'Username',
            'desc': u"Username you've signed up with."
        },
        'code': {
            'desc': u'As generated with google authenticator.'
        }
    }

    @property
    def allow_code_reminder(self):
        return self.req.registry['settings']['allowcodereminder']

    def send_code_reminder(self, user):
        mailer = self.req.registry['mailer']
        code_reminder_settings = \
            self.req.registry['settings']['allowcodereminder_settings'].copy()
        username = user.username
        message = code_reminder_settings.copy()
        message['recipients'] = [username]
        message['body'] = message['body'].replace('{code}',
            get_barcode_image(username, user.secret,
                self.req.registry['settings']['appname']))
        mailer.send(Message(**message))

    def check_code(self, user):
        tm = int(time.time() / 30)
        code_attempt = self.cform.data['code']
        # try 30 seconds behind and ahead as well
        for ix in [-1, 0, 1]:
            code = get_google_auth_code(user.secret, tm + ix)

            if not strings_differ(code, str(code_attempt)):
                return True
        return False


addFactoredPlugin(GoogleAuthPlugin)


class EmailAuthSchema(UsernameSchema):
    username = validators.Email(not_empty=True)


class EmailAuthCodeSchema(CodeSchema):
    username = validators.Email(not_empty=True)
    code = validators.MinLength(8, not_empty=True)


class EmailAuthPlugin(BasePlugin):
    name = 'Email'
    path = 'em'
    username_schema = EmailAuthSchema
    code_schema = EmailAuthCodeSchema

    _formtext_overrides = {
        'title': u'Email Authenticator',
        'legend': u'Authenticate through your email...',
        'username': {
            'label': u'Email',
            'desc': u'Email you signed up with. Should be ' + \
                    u'the same as the username.'
            },
        'code': {
            'desc': u'Provided in the email sent to you.'
        },
        'button': {
            'username': u'Send mail'
        }
    }

    def __init__(self, req):
        super(EmailAuthPlugin, self).__init__(req)
        self.message_settings = req.registry['settings']['email_auth_settings']

    def user_form_submitted_successfully(self, user):
        username = self.uform.data['username']
        mailer = self.req.registry['mailer']
        user.generated_code = make_random_code(12)
        user.generated_code_time_stamp = datetime.utcnow()

        message = self.message_settings.copy()
        message['recipients'] = [username]
        message['body'] = message['body'].replace('{code}',
            user.generated_code)
        mailer.send(Message(**message))

    def check_code(self, user):
        window = self.req.registry['settings']['email_auth_window']
        now = datetime.utcnow()
        return (not strings_differ(self.cform.data['code'], user.generated_code)) and \
                (now < (user.generated_code_time_stamp + timedelta(seconds=window)))


addFactoredPlugin(EmailAuthPlugin)
