import unittest

import jwt
from pyramid import testing

from factored.plugins import get_plugin_settings, get_manager


class JWTTests(unittest.TestCase):
    def test_generate_jwt(self):
        from factored.authenticator import generate_jwt

        settings = {
            'jwt.audience': 'urn:factored',
            'jwt.algorithm': 'HS512',
            'jwt.secret': 'supersecret',
            'jwt.cookie.name': 'testcookie',
            'jwt.cookie.age': 300,
            'jwt.cookie.secure': 'false',
            'jwt.cookie.httponly': 'false',
        }
        validtoken = jwt.encode(
            dict(
                sub='test@localhost.localdomain',
                exp=4108026419,
                aud='urn:factored',
            ),
            'supersecret',
            algorithm='HS512')

        # see the factored/validator/tests.py file for the details about
        # the example token used here
        cname, cage, csec, chttponly, enctoken = generate_jwt(settings, "test@localhost.localdomain")

        # decoding the token should work without exception if it was generated successfully
        jwt.decode(enctoken, 'supersecret', audience='urn:factored', algorithms=["HS512"])

        self.assertEqual(cname, "testcookie")
        self.assertEqual(cage, 300)
        self.assertEqual(csec, False)
        self.assertEqual(chttponly, False)


class AuthenticateViewTests(unittest.TestCase):
    def setUp(self):
        settings = {
            'jwt.audience': 'urn:factored',
            'jwt.algorithm': 'HS512',
            'jwt.secret': 'testsecret',
            'jwt.cookie.name': 'testcookie',
            'jwt.cookie.age': 300,
            'jwt.cookie.secure': 'false',
            'jwt.cookie.httponly': 'false',
            'plugins.dirs': '/app/factored/plugins/',
            'plugins.template': 'DefaultTemplate',
            'plugins.datastore': 'MemDataStore',
            'plugins.finder': 'EMailDomain',
            'plugin.EMailDomain.valid_domains': 'wildcardcorp.com\n   assemblys.net',
            'plugin.EMailAuth.code_timeout': '300',
            'plugin.EMailAuth.code_length': '6',
            'plugin.EMailAuth.code_hash_salt': '1XlPyGtXI2',
            'plugin.EMailAuth.mail.host': 'debugmailer',
            'plugin.EMailAuth.mail.port': '2525',
            'plugin.EMailAuth.subject': 'Authentication Request',
            'plugin.EMailAuth.sender': 'factored@localhost.localdomain',
            'plugin.EMailAuth.body_template': 'You have requested authentication.\nYour temporary access code is: {code}',
        }

        # normally created when an app is created
        plugindirs = settings['plugins.dirs'].splitlines()
        plugins = get_manager(plugindirs)
        settings["plugins.manager"] = plugins

        # setup template
        settings["templatesettings"] = get_plugin_settings("plugins.template", settings)

        # setup the configured datastore
        dspluginname = settings.get("plugins.datastore", "MemDataStore")
        dspluginsettings = get_plugin_settings("plugins.datastore", settings)
        ds = plugins.getPluginByName(dspluginname, category="datastore")
        ds.plugin_object.initialize(dspluginsettings)
        settings["datastore"] = ds

        # setup finder
        findersettings = get_plugin_settings("plugins.finder", settings)
        findername = settings.get("plugins.finder", None)
        finder = plugins.getPluginByName(findername, category="finder")
        finder.plugin_object.initialize(findersettings)
        settings["finder"] = finder

        self.config = testing.setUp(settings=settings)

    def tearDown(self):
        testing.tearDown()

    #def test_no_token(self):
    #    from factored.authenticator import authenticate
    #
    #    request = testing.DummyRequest()
    #    response = validate(request)
    #    self.assertEqual(response.status_code, 403)

    def test_authtype(self):
        from factored.authenticator import get_authtype

        req = testing.DummyRequest()
        authtype = get_authtype(req)
        self.assertEqual(authtype, None)

        req = testing.DummyRequest(params={'authtype': 'fictional'})
        authtype = get_authtype(req)
        self.assertEqual(authtype, 'fictional')

        req = testing.DummyRequest(params={'submit': 'authtype_fictional'})
        authtype = get_authtype(req)
        self.assertEqual(authtype, 'fictional')

        req = testing.DummyRequest(params={'submit': 'fictional'})
        authtype = get_authtype(req)
        self.assertNotEqual(authtype, 'fictional')

        req = testing.DummyRequest(params={'authtype': 'fictional1', 'submit': 'authtype_fictional2'})
        authtype = get_authtype(req)
        self.assertEqual(authtype, 'fictional2')

        req = testing.DummyRequest(params={'authtype': 'fictional1', 'submit': 'fictional2'})
        authtype = get_authtype(req)
        self.assertEqual(authtype, 'fictional1')

    def test_auth_notype(self):
        from factored.authenticator import authenticate

        # options form
        req = testing.DummyRequest()
        resp = authenticate(req)
        self.assertEquals(resp.status_code, 200)
        self.assertIn('class="pure-form option-form"', resp.text)

    def test_auth_typeselected(self):
        from factored.authenticator import authenticate

        # auth type has been selected
        req = testing.DummyRequest(params={'submit': 'authtype_EMailAuth'})
        resp = authenticate(req)
        self.assertEquals(resp.status_code, 200)
        self.assertIn('class="pure-form auth-form"', resp.text)

    def test_auth_emailsubmitted(self):
        from factored.authenticator import authenticate

        # auth type has been selected, email submitted
        req = testing.DummyRequest(params={
            'authtype': 'EMailAuth',
            'submit': 'email',
            'email': 'test@wildcardcorp.com',
        })
        resp = authenticate(req)
        self.assertEquals(resp.status_code, 200)
        self.assertIn('<input type="hidden" name="email" value="test@wildcardcorp.com" />', resp.text)

    def test_auth_codesubmitted(self):
        from factored.authenticator import authenticate

        # auth type selected, email submitted, invalid code submitted
        req = testing.DummyRequest(params={
            'authtype': 'EMailAuth',
            'submit': 'email',
            'email': 'test@wildcardcorp.com',
            'code': 'clearlywrong',
        })
        resp = authenticate(req)
        self.assertEquals(resp.status_code, 200)
        self.assertIn('class="error-box"', resp.text)

        # TODO test valid submission
