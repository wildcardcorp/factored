import unittest
import transaction

from pyramid import testing

from factored.models import DBSession
from factored.utils import generate_random_google_code
from pyramid.httpexceptions import HTTPFound
from repoze.who.plugins.auth_tkt import make_plugin
from repoze.who.api import APIFactory
from repoze.who.classifiers import default_request_classifier
from repoze.who.classifiers import default_challenge_decider
from datetime import timedelta


class FakeMailer(object):

    def __init__(self):
        self.messages = []

    def send(self, message):
        self.messages.append(message)


class BaseTest(unittest.TestCase):

    def get_request(self, *args, **kwargs):
        if 'environ' not in kwargs:
            kwargs['environ'] = {}
        if 'post' in kwargs:
            post = True
        else:
            post = False
        kwargs['environ'].update({
            'SCRIPT_NAME': '',
            'REQUEST_METHOD': post and 'POST' or 'GET',
            'PATH_INFO': '/',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'QUERY_STRING': '',
            'CONTENT_LENGTH': '0',
            'HTTP_ACCEPT_CHARSET': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            'HTTP_USER_AGENT': 'TEST',
            'HTTP_CONNECTION': 'keep-alive',
            'SERVER_NAME': '127.0.0.1',
            'REMOTE_ADDR': '127.0.0.1',
            'wsgi.url_scheme': 'http',
            'SERVER_PORT': '8000',
            'HTTP_HOST': '127.0.0.1:8000',
            'wsgi.multithread': True,
            'wsgi.version': (1, 0),
            'wsgi.run_once': False})
        req = testing.DummyRequest(*args, **kwargs)
        auth_tkt = make_plugin(secret="secret", cookie_name="test")
        req.registry['settings'] = {
            'email_auth_settings': {
                'subject': 'Authentication Request',
                'sender': 'foo@bar.com',
                'body': "You're temporary access code is: {code}"},
            'auth_tkt': auth_tkt,
            'email_auth_window': 120,
            'static_path': '/auth/static'
        }
        req.environ['who_api'] = APIFactory(
            [('auth_tkt', auth_tkt)],
            [('auth_tkt', auth_tkt)], [], [],
            default_request_classifier, default_challenge_decider)(req.environ)
        req.registry['mailer'] = self.mailer
        return req

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def setUp(self):
        self.config = testing.setUp()
        from sqlalchemy import create_engine
        engine = create_engine('sqlite://')
        from factored.models import Base
        DBSession.configure(bind=engine)
        Base.metadata.create_all(engine)
        self.mailer = FakeMailer()


class TestGoogleAuth(BaseTest):

    def setUp(self):
        super(TestGoogleAuth, self).setUp()
        from factored.models import User
        with transaction.manager:
            self.user = User(username='foo',
                secret=generate_random_google_code())
            DBSession.add(self.user)

    def test_blank_form(self):
        from factored.auth import GoogleAuthView
        request = self.get_request()
        info = GoogleAuthView(request)()
        renderer = info['uform']
        form = renderer.form
        self.assertTrue('username' not in form.data)

    def test_submit_without_username(self):
        from factored.auth import GoogleAuthView
        request = self.get_request(post={'submit': 'Next'})
        info = GoogleAuthView(request)()
        renderer = info['uform']
        form = renderer.form
        self.assertTrue('username' in form.errors)

    def test_submit_with_wrong_code(self):
        from factored.auth import GoogleAuthView
        request = self.get_request(
            post={'submit': 'Authenticate',
                  'username': 'foo',
                  'code': '377474'})
        info = GoogleAuthView(request)()
        renderer = info['cform']
        form = renderer.form
        self.assertTrue('username' not in form.errors)
        self.assertTrue('code' in form.errors)

    def test_submit_with_wrong_username(self):
        from factored.auth import GoogleAuthView
        request = self.get_request(
            post={'submit': 'Authenticate',
                  'username': 'bar',
                  'code': '377474'})
        info = GoogleAuthView(request)()
        renderer = info['cform']
        form = renderer.form
        self.assertTrue('code' in form.errors)

    def test_submit_success_with_code(self):
        from factored.auth import GoogleAuthView
        from factored.utils import get_google_auth_code
        from factored.models import User
        user = DBSession.query(User).filter_by(username='foo').first()
        request = self.get_request(
            post={'username': 'foo', 'submit': 'Authenticate',
                  'code': get_google_auth_code(user.secret)})
        with self.assertRaises(HTTPFound):
            GoogleAuthView(request)()

    def test_submit_success_with_code_check_headers(self):
        from factored.auth import GoogleAuthView
        from factored.utils import get_google_auth_code
        from factored.models import User
        user = DBSession.query(User).filter_by(username='foo').first()
        request = self.get_request(
            post={'username': 'foo', 'submit': 'Authenticate',
                  'code': get_google_auth_code(user.secret)})
        try:
            GoogleAuthView(request)()
        except HTTPFound, ex:
            self.assertTrue('test=' in ex.headers['Set-Cookie'])


class TestEmailAuth(BaseTest):

    def setUp(self):
        super(TestEmailAuth, self).setUp()
        from factored.models import User
        with transaction.manager:
            self.user = User(username='foo@bar.com',
                secret=generate_random_google_code())
            DBSession.add(self.user)

    def test_blank_form(self):
        from factored.auth import EmailAuthView
        request = self.get_request()
        info = EmailAuthView(request)()
        renderer = info['uform']
        form = renderer.form
        self.assertTrue('username' not in form.data)

    def test_not_send_mail_without_username(self):
        from factored.auth import EmailAuthView
        request = self.get_request(post={'submit': 'Send mail'})
        info = EmailAuthView(request)()
        renderer = info['uform']
        form = renderer.form
        self.assertTrue('username' in form.errors)

    def test_not_send_mail_with_incorrect_username_non_email(self):
        from factored.auth import EmailAuthView
        request = self.get_request(
            post={'submit': 'Send mail', 'username': 'foobar'})
        info = EmailAuthView(request)()
        renderer = info['uform']
        form = renderer.form
        self.assertTrue('username' in form.errors)

    def test_not_send_mail_with_incorrect_username(self):
        from factored.auth import EmailAuthView
        request = self.get_request(
            post={'submit': 'Send mail', 'username': 'blah@foo.com'})
        info = EmailAuthView(request)()
        renderer = info['uform']
        form = renderer.form
        self.assertTrue('username' in form.errors)

    def test_send_mail_with_correct_username(self):
        from factored.auth import EmailAuthView
        from factored.models import User
        request = self.get_request(
            post={'submit': 'Send mail', 'username': 'foo@bar.com'})
        info = EmailAuthView(request)()
        renderer = info['uform']
        form = renderer.form
        self.assertTrue(len(form.errors) == 0)
        self.assertTrue(len(self.mailer.messages) == 1)
        user = DBSession.query(User).filter_by(username='foo@bar.com').first()
        self.assertTrue(user.generated_code in self.mailer.messages[0].body)

    def test_auth_correct(self):
        from factored.auth import EmailAuthView
        from factored.models import User

        # first, set code
        request = self.get_request(
            post={'submit': 'Send mail', 'username': 'foo@bar.com'})
        EmailAuthView(request)()
        user = DBSession.query(User).filter_by(username='foo@bar.com').first()

        # then, auth with code
        request = self.get_request(
            post={'submit': 'Authenticate',
                  'username': 'foo@bar.com',
                  'code': user.generated_code})
        with self.assertRaises(HTTPFound):
            EmailAuthView(request)()

    def test_auth_correct_sets_headers(self):
        from factored.auth import EmailAuthView
        from factored.models import User

        # first, set code
        request = self.get_request(
            post={'submit': 'Send mail', 'username': 'foo@bar.com'})
        EmailAuthView(request)()
        user = DBSession.query(User).filter_by(username='foo@bar.com').first()

        # then, auth with code
        request = self.get_request(
            post={'submit': 'Authenticate',
                  'username': 'foo@bar.com',
                  'code': user.generated_code})
        try:
            EmailAuthView(request)()
        except HTTPFound, ex:
            self.assertTrue('test=' in ex.headers['Set-Cookie'])

    def test_auth_fails_bad_username(self):
        from factored.auth import EmailAuthView
        from factored.models import User

        # first, set code
        request = self.get_request(
            post={'submit': 'Send mail', 'username': 'foo@bar.com'})
        EmailAuthView(request)()
        user = DBSession.query(User).filter_by(username='foo@bar.com').first()

        # then, auth with code
        request = self.get_request(
            post={'submit': 'Authenticate',
                  'username': 'foo3@bar.com',
                  'code': user.generated_code
                  })
        info = EmailAuthView(request)()
        renderer = info['cform']
        form = renderer.form
        self.assertTrue(len(form.errors) == 1)
        self.assertTrue('code' in form.errors)
        self.assertTrue('Invalid username' in form.errors['code'])

    def test_auth_fails_missing_code(self):
        from factored.auth import EmailAuthView

        # first, set code
        request = self.get_request(
            post={'submit': 'Send mail', 'username': 'foo@bar.com'})
        EmailAuthView(request)()

        # then, auth with code
        request = self.get_request(
            post={'submit': 'Authenticate',
                  'username': 'foo@bar.com'})
        info = EmailAuthView(request)()
        renderer = info['cform']
        form = renderer.form
        self.assertTrue(len(form.errors) == 1)
        self.assertTrue('code' in form.errors)

    def test_auth_fails_bad_code(self):
        from factored.auth import EmailAuthView

        # first, set code
        request = self.get_request(
            post={'submit': 'Send mail', 'username': 'foo@bar.com'})
        EmailAuthView(request)()

        # then, auth with code
        request = self.get_request(
            post={'submit': 'Authenticate',
                  'username': 'foo@bar.com',
                  'code': 'random'})
        info = EmailAuthView(request)()
        renderer = info['cform']
        form = renderer.form
        self.assertTrue(len(form.errors) == 1)
        self.assertTrue('code' in form.errors)

    def test_auth_fails_time_limit(self):
        from factored.auth import EmailAuthView
        from factored.models import User

        # first, set code
        request = self.get_request(
            post={'submit': 'Send mail', 'username': 'foo@bar.com'})
        EmailAuthView(request)()
        user = DBSession.query(User).filter_by(username='foo@bar.com').first()

        # set time back
        user.generated_code_time_stamp = \
            user.generated_code_time_stamp - timedelta(seconds=121)
        # then, auth with code
        request = self.get_request(
            post={'submit': 'Authenticate',
                  'username': 'foo@bar.com',
                  'code': user.generated_code
                  })
        info = EmailAuthView(request)()
        renderer = info['cform']
        form = renderer.form
        self.assertTrue(len(form.errors) == 1)
        self.assertTrue('code' in form.errors)


if __name__ == '__main__':
    unittest.main()
