import unittest

from pyramid import testing

from factored.plugins import get_plugin_settings, get_manager


# NOTE: to encode or decode a JWT value for testing, see
#   https://jwt.io/#debugger-io
#
# for this file's tests, assume the following jwt values:
#
#   HEADER:
#       {
#           "alg": "HS512",
#           "typ": "JWT"
#       }
#   PAYLOAD:
#       {
#           "iss": "factored",
#           "sub": "test@localhost.localdomain.local",
#           "aud": "urn:factored",
#           "exp": 4108026419,
#           "iat": 952352819,
#       }
#   VERIFY SIGNATURE:
#       HMACSHA512(
#           base64UrlEncode(header)
#           +"."
#           +base64UrlEncode(payload)
#           +"."
#           +"testsecret"
#       )
#
# The above provides the following token:
#
#   eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmYWN0b3JlZCIsInN1YiI6InRlc3RAbG9jYWxob3N0LmxvY2FsZG9tYWluLmxvY2FsIiwiYXVkIjoidXJuOmZhY3RvcmVkIiwiZXhwIjo0MTA4MDI2NDE5LCJpYXQiOjE1MTYyMzkwMjJ9.xu4VpNtj41RLRKr80ysRnX89GAobSq8SZ8ZGdwLTB2fkf01hFdUlPvmeBF0Mne8_2AUIKYuwH9J51IMakLJP_g
#
#
# NOTES about the jwt values:
#   - 'sub' is the factored username/id passed to a userfinder
#   - the exp above represents a date in the year 2100, if you must change it'
#       I recommend using https://www.epochconverter.com
#   - the iat above represents a date in the year 2000
#


class ValidateViewTests(unittest.TestCase):
    def setUp(self):
        settings = {
            'jwt.audience': 'urn:factored',
            'jwt.algorithm': 'HS512',
            'jwt.secret': 'testsecret',
            'plugins.dirs': '/app/factored/plugins/',
            'plugins.finder': 'EMailDomain',
            'plugin.EMailDomain.valid_domains': 'wildcardcorp.com\n   assemblys.net',
        }

        # normally created when an app is created
        plugindirs = settings['plugins.dirs'].splitlines()
        plugins = get_manager(plugindirs)
        settings["plugins.manager"] = plugins

        # setup finder
        findersettings = get_plugin_settings("plugins.finder", settings)
        findername = settings.get("plugins.finder", None)
        finder = plugins.getPluginByName(findername, category="finder")
        finder.plugin_object.initialize(findersettings)
        settings["finder"] = finder

        self.config = testing.setUp(settings=settings)

    def tearDown(self):
        testing.tearDown()

    def test_no_token(self):
        from factored.validator import validate

        request = testing.DummyRequest()
        response = validate(request)
        self.assertEqual(response.status_code, 403)

    # the token may be valid, but the finder plugin may not indicate the subject
    # of the token is valid as well
    # NOTE: this uses the basic "emaildomain" finder but isn't specifically testing
    # to make sure that finder is working properly, the intent is to ensure the
    # validator view is working properly when configured with a validator.
    def test_valid_token_invalid_subject(self):
        from factored.validator import validate

        request = testing.DummyRequest(
            params={
                'token': 'eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmYWN0b3JlZCIsInN1YiI6InRlc3RAbG9jYWxob3N0LmxvY2FsZG9tYWluLmxvY2FsIiwiYXVkIjoidXJuOmZhY3RvcmVkIiwiZXhwIjo0MTA4MDI2NDE5LCJpYXQiOjE1MTYyMzkwMjJ9.xu4VpNtj41RLRKr80ysRnX89GAobSq8SZ8ZGdwLTB2fkf01hFdUlPvmeBF0Mne8_2AUIKYuwH9J51IMakLJP_g'
            })
        response = validate(request)
        self.assertEqual(response.status_code, 403)

    # the token may be valid, but the finder plugin may not indicate the subject
    # of the token is valid as well
    # NOTE: this uses the basic "emaildomain" finder but isn't specifically testing
    # to make sure that finder is working properly, the intent is to ensure the
    # validator view is working properly when configured with a validator.
    def test_valid_token_valid_subject(self):
        from factored.validator import validate

        # NOTE: the HEADERS, PAYLOAD, and VERIFY SIGNATURE used to generate the
        # following token are the same as the example, but with
        # a sub value of: test@wildcardcorp.com
        request = testing.DummyRequest(
            params={
                'token': 'eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmYWN0b3JlZCIsInN1YiI6InRlc3RAd2lsZGNhcmRjb3JwLmNvbSIsImF1ZCI6InVybjpmYWN0b3JlZCIsImV4cCI6NDEwODAyNjQxOSwiaWF0IjoxNTE2MjM5MDIyfQ.4I93TkJrxk8D4EKr2UFnAzEOcLc57K_za_tKUFCWna-Q25gIUtNeuF1foq1kBByOEpsAbJkUsZzeMvGYjc272A'
            })
        response = validate(request)
        self.assertEqual(response.status_code, 200)

    def test_expired_token(self):
        from factored.validator import validate

        # NOTE: the HEADERS, PAYLOAD, and VERIFY SIGNATURE used to generate the
        # following token are the same as the example, but with the exp date
        # set to 1488812846, which is a date/time in 2017
        request = testing.DummyRequest(
            params={
                'token': 'eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmYWN0b3JlZCIsInN1YiI6InRlc3RAbG9jYWxob3N0LmxvY2FsZG9tYWluLmxvY2FsIiwiYXVkIjoidXJuOmZhY3RvcmVkIiwiZXhwIjoxNDg4ODEyODQ2LCJpYXQiOjE1MTYyMzkwMjJ9._8K6etRvx--XfSmhjYhCqmhDFQDL5N0cDK0Ldf6mOErBe0ch1CpapNCOkUT_qMp1YPiXjW1ZbTPMfxbtVKtY9Q'
            })
        response = validate(request)
        self.assertEqual(response.status_code, 403)

    def test_no_subject(self):
        from factored.validator import validate

        # NOTE: the HEADERS, PAYLOAD, and VERIFY SIGNATURE used to generate the
        # following token are the same as the example, but with no sub value
        request = testing.DummyRequest(
            params={
                'token': 'eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmYWN0b3JlZCIsImF1ZCI6InVybjpmYWN0b3JlZCIsImV4cCI6MTQ4ODgxMjg0NiwiaWF0IjoxNTE2MjM5MDIyfQ.nrtrb1FeVKjniogy6vM5Hye1O1ZSN8-6tChcUClzYQfcSIdPSZeZryfZ5uY4B7qjBwf_4G9zRLlbxEa1NvtLlQ'
            })
        response = validate(request)
        self.assertEqual(response.status_code, 403)

