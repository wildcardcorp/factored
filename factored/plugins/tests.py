import os
import unittest

from pyramid import testing


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.defaults_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "defaults")

    def tearDown(self):
        testing.tearDown()

    def test_get_manager(self):
        from factored.plugins import get_manager

        manager = get_manager()
        locator = manager.getPluginLocator()
        self.assertIn(self.defaults_dir, locator.plugins_places)
        self.assertIsNotNone(manager.getPluginByName("EMailAuth", category="authenticator"))
        self.assertIsNone(manager.getPluginByName("EMailAuth"))
        self.assertIsNotNone(manager.getPluginByName("MemDataStore", category="datastore"))
        self.assertIsNotNone(manager.getPluginByName("SQLDataStore", category="datastore"))
        self.assertIsNotNone(manager.getPluginByName("EMailDomain", category="finder"))
        self.assertIsNotNone(manager.getPluginByName("MailerRegistration", category="registrar"))
        self.assertIsNotNone(manager.getPluginByName("DefaultSettings", category="settings"))
        self.assertIsNotNone(manager.getPluginByName("DefaultTemplate", category="template"))


#class EMailAuthPluginTest(unittest.TestCase):
    #def setUp(self):
        #self.defaults_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "defaults")
#
    #def tearDown(self):
        #testing.tearDown()
#
    #def test_get_manager(self):
        #from factored.plugins import get_manager
#
        #manager = get_manager()
        #emailauth = manager.getPluginByName("EMailAuth", category="authenticator")
        #plug = emailauth.plugin_object
#
        #self.assert
#
