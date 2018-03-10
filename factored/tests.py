import unittest

from pyramid import testing

from factored.plugins import get_plugin_settings


class PluginManagementTests(unittest.TestCase):
    def setUp(self):
        settings = {
            'plugins.dirs': '/app/factored/plugins/',
            'plugins.finder': 'emaildomain',
            'plugin.emaildomain.valid_domains': 'wildcardcorp.com\n   assemblys.net',
        }
        self.config = testing.setUp(settings=settings)

    def tearDown(self):
        testing.tearDown()

    def test_get_plugin_settings(self):
        psettings = get_plugin_settings("plugins.finder", self.config.registry.settings)

        self.assertIsNotNone(psettings)
        self.assertIn("valid_domains", psettings)
        self.assertNotIn("plugins.dirs", psettings)

        psettings = get_plugin_settings("plugin.emaildomain.", self.config.registry.settings, nolookup=True)
        self.assertIsNotNone(psettings)
        self.assertIn("valid_domains", psettings)
        self.assertNotIn("plugins.dirs", psettings)
