import unittest
from pyramid import testing
from factored.models import DBSession
from factored.utils import generate_random_google_code
from datetime import timedelta
from factored.app import Authenticator


class FakeMailer(object):

    def __init__(self):
        self.messages = []

    def send(self, message):
        self.messages.append(message)

    send_immediately = send


def test_application(environ, start_response):
    body = 'foobar'
    headers = [('Content-Type', 'text/html; charset=utf8'),
               ('Content-Length', str(len(body)))]
    start_response('200 Ok', headers)
    return [body]


class FakeApp(object):
    base_auth_url = '/auth'


class BaseTest(unittest.TestCase):

    def tearDown(self):
        self.session.close()
        testing.tearDown()

    def setUp(self):
        self.config = testing.setUp()
        self.settings = {
            'sqlalchemy.url': 'sqlite://',
            'em.subject': 'Authentication Request',
            'em.sender': 'foo@bar.com',
            'em.body': """
    You have requested authentication.
    Your temporary access code is: {code}""",
            'auth_tkt.secret': 'secret',
            'auth_tkt.cookie_name': 'pnutbtr',
            'supported_auth_schemes': [
                'Google Auth',
                'Email'
            ]
        }
        self.app = Authenticator(test_application, {}, **self.settings)
        from webtest import TestApp
        self.testapp = TestApp(self.app)
        self.mailer = FakeMailer()
        self.testapp.app.pyramid.registry['mailer'] = self.mailer
        from sqlalchemy import create_engine
        engine = create_engine('sqlite://')
        from factored.models import Base
        DBSession.configure(bind=engine)
        self.session = DBSession()
        Base.metadata.create_all(engine)


class TestSome(BaseTest):

    def setUp(self):
        super(TestSome, self).setUp()
        from factored.models import User
        self.user = User(
            username='foo@bar.com', secret=generate_random_google_code())
        self.session.add(self.user)
        self.session.commit()

    def test_redirect_to_auth(self):
        self.testapp.get('/', status=302)


class TestGoogleAuth(BaseTest):

    def setUp(self):
        super(TestGoogleAuth, self).setUp()
        from factored.models import User
        self.user = User(username='foo', secret=generate_random_google_code())
        self.session.add(self.user)

    def test_blank_form(self):
        resp = self.testapp.get('/auth/ga', status=200)
        resp.mustcontain('name="username')

    def test_submit_without_username_gives_error(self):
        resp = self.testapp.post('/auth/ga', status=200, params={
            'username': '',
            'submit': 'Next'
        })
        resp.mustcontain('class="error')

    def test_submit_with_wrong_code(self):
        resp = self.testapp.post('/auth/ga', status=200, params={
            'submit': 'Authenticate',
            'username': 'foo',
            'code': '377474'
        })
        resp.mustcontain('class="error')
        resp.mustcontain('Invalid username')

    def test_submit_success_with_code(self):
        from factored.utils import get_google_auth_code
        from factored.models import User
        user = self.session.query(User).filter_by(username='foo').first()
        self.testapp.post('/auth/ga', status=302, params={
            'submit': 'Authenticate',
            'username': 'foo',
            'code': get_google_auth_code(user.secret)
        })
        self.testapp.get('/')

    def test_submit_success_with_code_check_headers(self):
        from factored.utils import get_google_auth_code
        from factored.models import User
        user = self.session.query(User).filter_by(username='foo').first()
        resp = self.testapp.post('/auth/ga', status=302, params={
            'submit': 'Authenticate',
            'username': 'foo',
            'code': get_google_auth_code(user.secret)
        })
        assert 'pnutbtr=' in resp.headers['Set-Cookie']


class TestEmailAuth(BaseTest):

    def setUp(self):
        super(TestEmailAuth, self).setUp()
        from factored.models import User
        self.user = User(
            username='foo@bar.com', secret=generate_random_google_code())
        self.session.add(self.user)
        self.session.commit()

    def test_email_blank_form(self):
        resp = self.testapp.get('/auth/em', status=200)
        resp.mustcontain('name="username')

    def test_not_send_mail_without_username(self):
        resp = self.testapp.post('/auth/em', status=200, params={
            'submit': 'Send mail'
        })
        resp.mustcontain('class="error')

    def test_not_send_mail_with_incorrect_username_non_email(self):
        resp = self.testapp.post('/auth/em', status=200, params={
            'submit': 'Send mail',
            'username': 'foobar'
        })
        resp.mustcontain('class="error')
        resp.mustcontain('must contain a single @')

    def test_not_send_mail_with_incorrect_username(self):
        resp = self.testapp.post('/auth/em', status=200, params={
            'submit': 'Send mail',
            'username': 'blah@foo.com'
        })
        resp.mustcontain('class="error')
        assert 'must contain a single @' not in resp.body
        resp.mustcontain('Should be the same as the username.')

    def test_send_mail_with_correct_username(self):
        from factored.models import User
        resp = self.testapp.post('/auth/em', status=200, params={
            'submit': 'Send mail',
            'username': 'foo@bar.com'
        })
        user = self.session.query(User).filter_by(
            username='foo@bar.com').first()
        assert 'class="error' not in resp.body
        self.assertTrue(len(self.mailer.messages) == 1)
        self.assertTrue(user.generated_code in self.mailer.messages[0].body)

    def test_send_mail_with_correct_username_case_insensitive(self):
        from factored.models import User
        resp = self.testapp.post('/auth/em', status=200, params={
            'submit': 'Send mail',
            'username': 'FOO@BAR.com'
        })
        user = self.session.query(User).filter_by(
            username='foo@bar.com').first()
        assert 'class="error' not in resp.body
        self.assertTrue(len(self.mailer.messages) == 1)
        self.assertTrue(user.generated_code in self.mailer.messages[0].body)

    def test_auth_correct(self):
        from factored.models import User
        self.testapp.post('/auth/em', status=200, params={
            'submit': 'Send mail',
            'username': 'foo@bar.com'
        })
        user = self.session.query(User).filter_by(
            username='foo@bar.com').first()
        self.testapp.post('/auth/em', status=302, params={
            'submit': 'Authenticate',
            'username': 'foo@bar.com',
            'code': user.generated_code
        })
        self.testapp.get('/')

    def test_auth_correct_sets_headers(self):
        from factored.models import User
        self.testapp.post('/auth/em', status=200, params={
            'submit': 'Send mail',
            'username': 'foo@bar.com'
        })
        user = self.session.query(User).filter_by(
            username='foo@bar.com').first()
        resp = self.testapp.post('/auth/em', status=302, params={
            'submit': 'Authenticate',
            'username': 'foo@bar.com',
            'code': user.generated_code
        })
        assert 'pnutbtr=' in resp.headers['Set-Cookie']

    def test_auth_fails_bad_username(self):
        from factored.models import User
        self.testapp.post('/auth/em', status=200, params={
            'submit': 'Send mail',
            'username': 'foo@bar.com'
        })
        user = self.session.query(User).filter_by(
            username='foo@bar.com').first()
        resp = self.testapp.post('/auth/em', status=200, params={
            'submit': 'Authenticate',
            'username': 'foo3@bar.com',
            'code': user.generated_code
        })
        resp.mustcontain('class="error')

    def test_auth_fails_missing_code(self):
        self.testapp.post('/auth/em', status=200, params={
            'submit': 'Send mail',
            'username': 'foo@bar.com'
        })
        resp = self.testapp.post('/auth/em', status=200, params={
            'submit': 'Authenticate',
            'username': 'foo@bar.com'
        })
        resp.mustcontain('class="error')

    def test_auth_fails_bad_code(self):
        self.testapp.post('/auth/em', status=200, params={
            'submit': 'Send mail',
            'username': 'foo@bar.com'
        })
        resp = self.testapp.post('/auth/em', status=200, params={
            'submit': 'Authenticate',
            'username': 'foo@bar.com',
            'code': 'random'
        })
        resp.mustcontain('class="error')

    def test_auth_fails_time_limit(self):
        from factored.models import User
        self.testapp.post('/auth/em', status=200, params={
            'submit': 'Send mail',
            'username': 'foo@bar.com'
        })
        user = self.session.query(User).filter_by(
            username='foo@bar.com').first()
        user.generated_code_time_stamp = \
            user.generated_code_time_stamp - timedelta(seconds=121)
        self.session.commit()
        resp = self.testapp.post('/auth/em', status=200, params={
            'submit': 'Authenticate',
            'username': 'foo@bar.com',
            'code': user.generated_code
        })
        resp.mustcontain('class="error')
