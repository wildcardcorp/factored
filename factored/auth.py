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
from factored.utils import create_user
from factored.utils import get_barcode_image
import copy

_auth_plugins = []


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


class UsernameSchema(BaseSchema):
    username = validators.MinLength(3, not_empty=True)
    referrer = validators.UnicodeString(if_missing=u'')


class CodeSchema(BaseSchema):
    username = validators.MinLength(3, not_empty=True)
    code = validators.MinLength(4, not_empty=True)
    remember = validators.Bool()
    referrer = validators.UnicodeString(if_missing=u'')


class BaseAuthView(object):
    name = None
    path = None
    username_schema = UsernameSchema
    code_schema = CodeSchema
    renderer = "templates/auth.pt"

    formtext = {
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

    def __init__(self, req):
        self.req = req
        self.uform = Form(req, schema=self.username_schema)
        self.cform = Form(req, schema=self.code_schema)
        self.message_settings = req.registry['settings']['email_auth_settings']
        self.send_submitted = self.validate_submitted = False
        self.googleauthcodereminder_settings = \
            req.registry['settings']['allowgooglecodereminder_settings']
        self.auth_timeout = req.registry['settings']['auth_timeout']
        self.auth_remember_timeout = \
            req.registry['settings']['auth_remember_timeout']
        rto = self.auth_remember_timeout / 60
        if rto > 60:
            rto = rto / 60
            if rto > 24:
                rto = '%i days' % (rto / 24)
            else:
                rto = '%i hours' % rto
        else:
            rto = '%i minutes' % rto
        self.remember_duration = rto

    @property
    def allowgooglecodereminder(self):
        return self.req.registry['settings']['allowgooglecodereminder'] and \
            self.name == 'Google Auth'

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

    def __call__(self):
        req = self.req
        if req.method == "POST":
            if req.POST.get('submit', '') == self.formtext['button']['codereminder'] \
                    and self.allowgooglecodereminder:
                self.validate_submitted = True
                self.cform.validate()
                self.cform.errors['code'] = self.error_code_reminder
                username = self.cform.data['username']
                user = self.get_user(username)
                if 'username' not in self.cform.errors and user is not None:
                    mailer = self.req.registry['mailer']
                    message = self.googleauthcodereminder_settings.copy()
                    message['recipients'] = [username]
                    message['body'] = message['body'].replace('{code}',
                        get_barcode_image(username, user.secret,
                            self.req.registry['settings']['appname']))
                    mailer.send(Message(**message))
            elif req.POST.get('submit', '') == self.formtext['button']['username']:
                if self.uform.validate():
                    username = self.uform.data['username']
                    self.cform.data['username'] = username
                    user = self.get_user(username)
                    if user is None:
                        self.uform.errors['username'] = \
                            self.formtext['error']['invalid_username']
                    else:
                        self.send_submitted = True
                        self.user_form_submitted_successfully(user)
            elif req.POST.get('submit', '') == self.formtext['button']['authenticate']:
                self.validate_submitted = True
                if self.cform.validate():
                    user = self.get_user(self.cform.data['username'])
                    if user is None:
                        self.cform.errors['code'] = \
                            self.formtext['error']['invalid_username_code']
                    else:
                        if self.check_code(user):
                            userid = self.cform.data['username']
                            if self.cform.data['remember']:
                                max_age = self.auth_remember_timeout
                            else:
                                max_age = self.auth_timeout
                            auth = self.req.environ['auth']
                            headers = auth.remember(userid, max_age=max_age)
                            referrer = self.cform.data.get('referrer')
                            if not referrer:
                                referrer = '/'
                            raise HTTPFound(location=referrer, headers=headers)
                        else:
                            self.cform.errors['code'] = self.formtext['error']['invalid_code']
                            self.cform.data['code'] = u''
        referrer = self.cform.data.get('referrer',
            self.uform.data.get('referrer', req.params.get('referrer', '')))
        self.uform.data.update({'referrer': referrer})
        self.cform.data.update({'referrer': referrer})
        return get_context(req, uform=FormRenderer(self.uform),
            cform=FormRenderer(self.cform), send_submitted=self.send_submitted,
            validate_submitted=self.validate_submitted,
            formtext=self.formtext, allowgooglecodereminder=self.allowgooglecodereminder,
            remember_duration=self.remember_duration)


class GoogleAuthView(BaseAuthView):
    name = 'Google Auth'
    path = 'ga'

    formtext = copy.deepcopy(BaseAuthView.formtext)
    formtext.update({
        'title': u'Google Authenticator',
        'legend': u'Use android app to authenticate...'
        })
    formtext['username'].update({
        'label': u'Username',
        'desc': u"Username you've signed up with."
    })
    formtext['code']['desc'] = u'As generated with google authenticator.'

    def check_code(self, user):
        tm = int(time.time() / 30)
        code_attempt = self.cform.data['code']
        # try 30 seconds behind and ahead as well
        for ix in [-1, 0, 1]:
            code = get_google_auth_code(user.secret, tm + ix)

            if code == str(code_attempt):
                return True
        return False


addFactoredPlugin(GoogleAuthView)


class EmailAuthSchema(UsernameSchema):
    username = validators.Email(not_empty=True)


class EmailAuthCodeSchema(CodeSchema):
    username = validators.Email(not_empty=True)
    code = validators.MinLength(8, not_empty=True)


class EmailAuthView(BaseAuthView):
    name = 'Email'
    path = 'em'
    username_schema = EmailAuthSchema
    code_schema = EmailAuthCodeSchema

    formtext = copy.deepcopy(BaseAuthView.formtext)
    formtext.update({
        'title': u'Email Authenticator',
        'legend': u'Authenticate through your email...'
        })
    formtext['username'].update({
        'label': u'Email',
        'desc': u'Email you signed up with. Should be ' + \
                u'the same as the username.'
    })
    formtext['code'].update({
        'desc': u'Provided in the email sent to you.'
    })

    formtext['button']['username'] = u'Send mail'

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
        return self.cform.data['code'] == user.generated_code and \
            now < (user.generated_code_time_stamp + timedelta(seconds=window))


addFactoredPlugin(EmailAuthView)
