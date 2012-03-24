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


class CodeSchema(BaseSchema):
    username = validators.MinLength(3, not_empty=True)
    code = validators.MinLength(4, not_empty=True)


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

    error_invalid_username_code = u'Invalid username for this code'
    error_invalid_code = u'Code did not validate'
    error_invalid_username = u'Invalid username'

    username_schema = UsernameSchema
    code_schema = CodeSchema

    renderer = "templates/auth.pt"

    def __init__(self, req):
        self.req = req
        self.uform = Form(req, schema=self.username_schema)
        self.cform = Form(req, schema=self.code_schema)
        self.message_settings = req.registry['settings']['email_auth_settings']
        self.send_submitted = self.validate_submitted = False

    def get_user(self, username):
        return DBSession.query(User).filter_by(username=username).first()

    def on_user_form_submitted_success(self, user):
        self.send_submitted = True

    def on_user_form_submitted_invalid_user(self):
        self.uform.errors['username'] = self.error_invalid_username

    def on_user_form_submitted(self):
        if self.uform.validate():
            username = self.uform.data['username']
            self.cform.data['username'] = username
            user = self.get_user(username)
            if user is None:
                self.on_user_form_submitted_invalid_user()
            else:
                self.on_user_form_submitted_success(user)

    def on_code_form_submitted_invalid_user(self):
        self.cform.errors['code'] = self.error_invalid_username_code

    def on_code_submitted_successfully(self):
        creds = {}
        creds['repoze.who.userid'] = self.cform.data['username']
        creds['identifier'] = self.req.registry['settings']['auth_tkt']
        who_api = self.req.environ['who_api']
        headers = who_api.remember(creds)
        raise HTTPFound(location='/', headers=headers)

    def check_code(self, user):
        return False

    def on_code_submitted_failure(self):
        self.cform.errors['code'] = self.error_invalid_code
        self.cform.data['code'] = u''

    def on_code_form_submitted_valid_user(self, user):
        if self.check_code(user):
            self.on_code_submitted_successfully()
        else:
            self.on_code_submitted_failure()

    def on_code_form_submitted(self):
        self.validate_submitted = True
        if self.cform.validate():
            user = self.get_user(self.cform.data['username'])
            if user is None:
                self.on_code_form_submitted_invalid_user()
            else:
                self.on_code_form_submitted_valid_user(user)

    def __call__(self):
        req = self.req
        if req.method == "POST":
            if req.POST.get('submit', '') == self.form_button_username:
                self.on_user_form_submitted()
            elif req.POST.get('submit', '') == self.form_button_authenticate:
                self.on_code_form_submitted()
        return get_context(req, uform=FormRenderer(self.uform),
            cform=FormRenderer(self.cform), send_submitted=self.send_submitted,
            validate_submitted=self.validate_submitted,
            form_button_username=self.form_button_username,
            form_button_authenticate=self.form_button_authenticate,
            form_title=self.form_title, form_legend=self.form_legend,
            form_username_label=self.form_username_label,
            form_username_desc=self.form_username_desc,
            form_code_label=self.form_code_label,
            form_code_desc=self.form_code_desc)


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


class EmailAuthSchema(BaseSchema):

    username = validators.Email(not_empty=True)


class EmailAuthCodeSchema(BaseSchema):
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

    def on_user_form_submitted_success(self, user):
        self.send_submitted = True
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
