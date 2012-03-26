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

    form_title = None
    form_legend = None
    form_username_label = None
    form_username_desc = None
    form_code_label = u'Access Code'
    form_code_desc = None

    form_button_username = u'Next'
    form_button_authenticate = u'Authenticate'
    form_button_codereminder = u'Send Code Reminder'

    error_invalid_username_code = u'Invalid username for this code'
    error_invalid_code = u'Code did not validate'
    error_invalid_username = u'Invalid username'
    error_code_reminder = u'A code reminder email has been sent.'

    username_schema = UsernameSchema
    code_schema = CodeSchema

    renderer = "templates/auth.pt"

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
            if req.POST.get('submit', '') == self.form_button_codereminder \
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
            elif req.POST.get('submit', '') == self.form_button_username:
                if self.uform.validate():
                    username = self.uform.data['username']
                    self.cform.data['username'] = username
                    user = self.get_user(username)
                    if user is None:
                        self.uform.errors['username'] = \
                            self.error_invalid_username
                    else:
                        self.send_submitted = True
                        self.user_form_submitted_successfully(user)
            elif req.POST.get('submit', '') == self.form_button_authenticate:
                self.validate_submitted = True
                if self.cform.validate():
                    user = self.get_user(self.cform.data['username'])
                    if user is None:
                        self.cform.errors['code'] = \
                            self.error_invalid_username_code
                    else:
                        if self.check_code(user):
                            creds = {}
                            creds['repoze.who.userid'] = \
                                self.cform.data['username']
                            creds['identifier'] = \
                                self.req.registry['settings']['auth_tkt']
                            if self.cform.data['remember']:
                                creds['max_age'] = self.auth_remember_timeout
                            else:
                                creds['max_age'] = self.auth_timeout
                            who_api = self.req.environ['who_api']
                            headers = who_api.remember(creds)
                            referrer = self.cform.data.get('referrer')
                            if not referrer:
                                referrer = '/'
                            raise HTTPFound(location=referrer, headers=headers)
                        else:
                            self.cform.errors['code'] = self.error_invalid_code
                            self.cform.data['code'] = u''
        referrer = self.cform.data.get('referrer',
            self.uform.data.get('referrer', req.params.get('referrer', '')))
        self.uform.data.update({'referrer': referrer})
        self.cform.data.update({'referrer': referrer})
        return get_context(req, uform=FormRenderer(self.uform),
            cform=FormRenderer(self.cform), send_submitted=self.send_submitted,
            validate_submitted=self.validate_submitted,
            form_button_username=self.form_button_username,
            form_button_authenticate=self.form_button_authenticate,
            form_button_codereminder=self.form_button_codereminder,
            form_title=self.form_title, form_legend=self.form_legend,
            form_username_label=self.form_username_label,
            form_username_desc=self.form_username_desc,
            form_code_label=self.form_code_label,
            form_code_desc=self.form_code_desc,
            allowgooglecodereminder=self.allowgooglecodereminder,
            remember_duration=self.remember_duration)


class GoogleAuthView(BaseAuthView):
    name = 'Google Auth'
    path = 'ga'

    form_title = u'Google Authenticator'
    form_legend = u'Use android app to authenticate...'
    form_username_label = u'Username'
    form_username_desc = u"Username you've signed up with."
    form_code_desc = u'As generated with google authenticator.'

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

    form_title = u'Email Authenticator'
    form_legend = u'Authenticate through your email...'
    form_username_label = u'Email'
    form_username_desc = u'Email you signed up with. Should be ' + \
                         u'the same as the username.'
    form_code_desc = u'Provided in the email sent to you.'

    username_schema = EmailAuthSchema
    code_schema = EmailAuthCodeSchema

    form_button_username = u'Send mail'

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
