from copy import deepcopy as copy
from datetime import datetime
from datetime import timedelta
from formencode import Schema, validators
import hashlib
import os
from pyramid.httpexceptions import HTTPFound
from pyramid.util import strings_differ
from pyramid_mailer.message import Message
from pyramid_simpleform import Form
from pyramid_simpleform.renderers import FormRenderer
import time
try:
    from urlparse import urlparse, parse_qsl
except ImportError:
    from urllib.parse import urlparse, parse_qsl

from factored.utils import CombinedDict
from factored.utils import get_barcode_image
from factored.utils import get_google_auth_code
from factored.utils import get_mailer
from factored.utils import make_random_code
from factored.utils import generate_url


_auth_plugins = []


def safe_headers(values):
    headers = []
    for name, value in values:
        if isinstance(value, unicode):
            value = value.encode('utf8')
        headers.append((name, value))
    return headers


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
    content_renderer = "templates/auth.pt"

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
        self.formtext = nested_update(copy(self._formtext),
                                      self._formtext_overrides)
        self.send_submitted = self.validate_submitted = False
        self.combined_formtext = CombinedDict(
            req.registry['formtext'], self.formtext)

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
    def app(self):
        return self.req.registry['app']

    @property
    def db(self):
        return self.app.db

    def get_user(self, username):
        user = self.db.get_user(self.req, username.lower())
        if user is None:
            if 'userfinder' in self.req.registry['settings']:
                finder = self.req.registry['settings']['userfinder']
                if finder(username):
                    return self.db.create_user(self.req, username)
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

    @property
    def settings(self):
        name = '%s_settings' % self.path
        if name in self.req.registry['settings']:
            return self.req.registry['settings'][name]
        else:
            return {}

    def update_referrer(self):
        referrer = self.uform.data.get('referrer',
                                       self.req.params.get('referrer', ''))
        referrer = self.cform.data.get('referrer', referrer)
        if not referrer:
            referrer = self.req.path_url
        # strip off auth url
        parts = self.req.environ['PATH_INFO'].rsplit('/')
        referrer = referrer.rstrip('/')
        if parts[-1] == self.path and \
                referrer.endswith(self.path):
            referrer = referrer[:-len(self.path)]
            parts.remove(self.path)
        referrer = referrer.rstrip('/')
        if referrer.endswith(parts[-1]):
            referrer = referrer[:-len(parts[-1])]
        self.uform.data.update({'referrer': referrer})
        self.cform.data.update({'referrer': referrer})

    @property
    def requesting_code_reminder(self):
        cm = self.formtext['button']['codereminder']
        acm = self.allow_code_reminder
        return self.req.POST.get('submit', '') == cm and acm

    def send_out_code_reminder(self):
        self.validate_submitted = True
        self.cform.validate()
        self.cform.errors['code'] = self.error_code_reminder
        username = self.cform.data['username'].lower()
        user = self.get_user(username)
        if 'username' not in self.cform.errors and user is not None:
            self.send_code_reminder(user)

    @property
    def requesting_user_form(self):
        return self.req.POST.get('submit', '') == \
            self.formtext['button']['username']

    def submit_user_form(self):
        if self.uform.validate():
            username = self.uform.data['username'].lower()
            self.cform.data['username'] = username
            user = self.get_user(username)
            if user is None:
                self.uform.errors['username'] = \
                    self.formtext['error']['invalid_username']
            else:
                self.send_submitted = True
                self.user_form_submitted_successfully(user)

    @property
    def requesting_authentication(self):
        return self.req.POST.get('submit', '') == \
            self.formtext['button']['authenticate']

    def submit_authentication(self):
        self.validate_submitted = True
        if self.cform.validate():
            user = self.get_user(self.cform.data['username'].lower())
            if user is None:
                self.cform.errors['code'] = \
                    self.formtext['error']['invalid_username_code']
            else:
                if self.check_code(user):
                    userid = self.cform.data['username'].lower()
                    if self.cform.data['remember']:
                        max_age = self.auth_remember_timeout
                    else:
                        max_age = self.auth_timeout
                    auth = self.req.environ['auth']
                    headers = safe_headers(auth.remember(userid, max_age=max_age))  # noqa
                    referrer = self.cform.data.get('referrer')
                    if not referrer:
                        referrer = '/'
                    raise HTTPFound(location=referrer, headers=headers)
                else:
                    self.cform.errors['code'] = \
                        self.formtext['error']['invalid_code']
                    self.cform.data['code'] = u''

    def render(self):
        req = self.req
        if req.method == "POST":
            if self.requesting_code_reminder:
                self.send_out_code_reminder()
            elif self.requesting_user_form:
                self.submit_user_form()
            elif self.requesting_authentication:
                self.submit_authentication()
        self.update_referrer()
        return dict(
            auth_plugin=self,
            uform=FormRenderer(self.uform),
            cform=FormRenderer(self.cform),
            send_submitted=self.send_submitted,
            validate_submitted=self.validate_submitted,
            content_renderer=self.content_renderer,
            formtext=self.combined_formtext,
            remember_duration=self.remember_duration)


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
        mailer = get_mailer(self.req)
        code_reminder_settings = \
            self.req.registry['settings']['allowcodereminder_settings'].copy()
        username = user.username
        message = code_reminder_settings.copy()
        message['recipients'] = [username]
        appname = self.req.registry['settings']['appname']
        message['body'] = message['body'].replace(
            '{code}', get_barcode_image(username, user.secret, appname))
        mailer.send_immediately(Message(**message))

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

    __formtext_overrides = {
        'title': u'Email Authenticator',
        'legend': u'Authenticate through your email...',
        'username': {
            'label': u'Email',
            'desc': u'Email you signed up with. Should be '
                    u'the same as the username.'
        },
        'code': {
            'desc': u'Provided in the email sent to you.'
        },
        'button': {
            'username': u'Send mail'
        }
    }

    @property
    def _formtext_overrides(self):
        overrides = self.__formtext_overrides.copy()
        if "{url}" in self.settings['body']:
            overrides['code']['desc'] = ('Provided in email sent to you in '
                                         'addition to an email link to login '
                                         'with automatically.')
        else:
            overrides['code']['desc'] = 'Provided in email sent to you.'
        return overrides

    def __init__(self, req):
        super(EmailAuthPlugin, self).__init__(req)

    def submit_authentication(self):
        urlcode = self.req.GET.get('code', None)
        if urlcode:
            referrer = self.req.params.get('referrer', '/')
            remember = self.req.params.get('rem', '0')
            remember = remember != '0'
            urlname = self.req.params.get('u', None)
            user = self.get_user(urlname.lower())
            # make sure the passed user is valid
            if user is None:
                self.cform.errors['code'] = \
                    self.formtext['error']['invalid_username_code']
                return
            # make sure the urlcode hash matches with the user id of the user
            #   identified from the url, generated code, and salt
            code = user.generated_code
            salt = self.settings.get('salt', 's4lt!necracker')
            newhash = hashlib.sha256(
                "%s%s%s" % (user.id, code, salt)).hexdigest()
            if newhash != urlcode:
                self.cform.errors['code'] = \
                    self.formtext['error']['invalid_code']
                return
            # check the code (make sure it's still valid and all that)
            #   note: even though this is comparing the same actual code value
            #   to itself, it's still checking to see if the code timed out,
            #   etc
            if self.check_code(user, user.generated_code):
                userid = user.username
                if remember:
                    max_age = self.auth_remember_timeout
                else:
                    max_age = self.auth_timeout
                auth = self.req.environ['auth']
                headers = safe_headers(auth.remember(userid, max_age=max_age))
                raise HTTPFound(location=referrer, headers=headers)
            else:
                self.cform.errors['code'] = \
                    self.formtext['error']['invalid_code']
                self.cform.data['code'] = u''
                return
        else:
            super(EmailAuthPlugin, self).submit_authentication()

    def user_form_submitted_successfully(self, user):
        username = self.uform.data['username']
        mailer = get_mailer(self.req)
        user.generated_code = make_random_code(12)
        user.generated_code_time_stamp = datetime.utcnow()
        # save it
        self.db.save(self.req, user)
        settings = self.settings

        # only generate the url if it's being used
        url = ''
        if "{url}" in settings['body']:
            salt = settings.get('salt', 's4lt!necracker')
            urlparts = list(urlparse(self.req.url))
            querystr = dict(parse_qsl(urlparts[4]))
            querystr['code'] = hashlib.sha256(
                "%s%s%s" % (user.id, user.generated_code, salt)) \
                .hexdigest()
            querystr['u'] = username
            querystr['rem'] = settings.get('url_remember', '0')
            querystr['rem'] = '1' if querystr['rem'] == 'True' else '0'
            url = generate_url(self.req, self.req.path, querystr)

        message = {
            'recipients': [username],
            'body': settings['body'].replace('{code}', user.generated_code)
                                    .replace('{url}', url),
            'subject': settings['subject'],
            'sender': settings['sender']
        }
        mailer.send_immediately(Message(**message))

    def check_code(self, user, code=None):
        window = self.req.registry['settings']['email_auth_window']
        now = datetime.utcnow()
        codetocheck = code if code else self.cform.data['code']
        return ((not strings_differ(codetocheck, user.generated_code))
                and (now < (user.generated_code_time_stamp +
                            timedelta(seconds=window))))

    def render(self):
        if self.req.GET.get('code', None):
            self.validate_submitted = True
            self.submit_authentication()

        return super(EmailAuthPlugin, self).render()


addFactoredPlugin(EmailAuthPlugin)
