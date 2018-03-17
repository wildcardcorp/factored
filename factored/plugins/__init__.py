import os
from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManager
from yapsy.PluginFileLocator import PluginFileLocator
from yapsy.PluginFileLocator import PluginFileAnalyzerMathingRegex
from yapsy.PluginInfo import PluginInfo

import logging
logger = logging.getLogger("factored.plugins")


def get_manager(plugin_dirs=None, plugin_dotted_names=None, load_defaults=True):
    """
    Keyword Arguments:
    plugin_dirs -- list of directory paths where plugins should be searched for
    plugin_dotted_names -- list of strings representing the dotted path of a python module
    load_defaults -- True to load the plugins included with factored

    Returns:
    A yapsy.PluginManager.PluginManager instance with all configured plugins loaded
    """
    if plugin_dirs is None or type(plugin_dirs) is not list:
        plugin_dirs = []
    if load_defaults:
        plugin_dirs.append(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "defaults")))

    # don't include py files that start with an understcore
    analyzer = PluginFileAnalyzerMathingRegex("pyfiles", "^.*\.py$")
    filelocator = PluginFileLocator(analyzers=[analyzer])
    filelocator.setPluginPlaces(plugin_dirs)

    manager = PluginManager()
    manager.setPluginLocator(filelocator)
    manager.setCategoriesFilter({
        "finder": IFinderPlugin,
        "authenticator": IAuthenticatorPlugin,
        "registrar": IRegistrationPlugin,
        "template": ITemplatePlugin,
        "datastore": IDataStorePlugin,
    })
    manager.collectPlugins()
    return manager


def get_plugin_settings(name_setting, allsettings, nolookup=False):
    """
    Arguments:
    name_setting -- configured setting that identifies the plugin by name,
                    eg "plugins.finder" for finder plugins. If "nolookup" is True,
                    then the name given in "name_setting" is considered the prefix
                    for the plugin settings.
    allsettings -- all configured settings to search through for plugin specific stuff

    Keyword Arguments:
    nolookup -- if True then name_setting will be the prefix to use to find all
                settings for the plugin
    """
    if nolookup:
        prefix = name_setting
    else:
        pname = allsettings.get(name_setting, None)
        if pname is None:
            logger.error("{pname} not configured".format(pname=name_setting))
            return None
        prefix = "plugin.{name}.".format(name=pname)
    setting_keys = [k for k in allsettings.keys() if k.startswith(prefix)]
    plugin_settings = {}
    for key in setting_keys:
        trimmed_key = key[len(prefix):]
        plugin_settings[trimmed_key] = allsettings[key]
    return plugin_settings


class IFinderPlugin(IPlugin):
    """
    IFinderPlugin's are used primarily in the factored.validator for the express
    purpose of approving or denying the subject of a given token
    """

    def is_valid_subject(self, settings, sub):
        """
        Arguments:
        settings -- dict of key-value config specific to the plugin
        sub -- "subject" aka unique user identifier

        Returns:
        should return True/False if the "sub" value is a valid user
        """
        raise NotImplemented()


class IAuthenticatorPlugin(IPlugin):
    """
    IAuthentictorPlugin's are used primarily in the factored.authenticator for
    the purpose of providing different methods of 2FA -- IE by email, by sms,
    by TOTP, and so on -- and (optionally) providing a way to request an
    account.
    """
    @property
    def display_name(self):
        """
        Returns:
        a string that represents a name that would otherwise be displayed
        to the user.
        """
        raise NotImplemented()

    def handle(self, settings, params, datastore, finder):
        """
        Arguments:
        settings -- dict of key-value config specific to the plugin
        params -- a dict of values from the combined GET and POST of the form
        datastore -- a IDataStorePlugin instance
        finder -- a IFinderPlugin instance

        Returns:
        a dict of values.
          - if the dict contains a key "authenticated" set to True, then the
            user has completed authentication and should have a jwt sent to them.
            In this case, there will also be a "subject" set to the users id.
          - if the dict DOES NOT contain "authenticated", then the dict is to be
            passed as the **kwargs of the render method call when 'template()'
            is rendered
        """
        raise NotImplemented()

    def template(self, settings, params):
        """
        Arguments:
        settings -- dict of key-value config specific to the plugin
        params -- a dict of values to be used within the template, generated by the
                  auth_handler method

        Returns:
        jinja2 template in the form of a string
        """
        return """{% extends "base.html" %}"""


class IRegistrationPlugin(IPlugin):
    """
    IRegistrationPlugin's are used to provide a template structure for the
    registration form when it is enabled and activated, and then to handle
    a registration submission.
    """
    def handle(self, settings, params, datastore, finder):
        """
        Arguments:
        settings -- dict of key-value config specific to the plugin
        params -- a dict of values from the combined GET and POST of the form
        datastore -- an IDataStorePlugin instance for use by the registration
                     plugin in saving data, may be None
        finder -- an IFinderPlugin instance for use in verifying a user

        Returns:
        a dict of values to be passed as the 'params' of the
        registration_template method.

        reserved keys for the return dict are 'state' and 'auth_options',
        using either may cause unexpected issues.
        """
        raise NotImplemented()

    def template(self, settings, params):
        """
        Arguments:
        settings -- dict of key-value config specific to the plugin
        params -- a dict of values to be used within the template, generated by the
                  registration_handler method
        """
        return """{% extends "base.html" %}"""


class ITemplatePlugin(IPlugin):
    """
    ITemplatePlugin's are used at the top level of the factored.authenticator to
    provide the layout/base template of the system. It is expected that the
    ITemplatePlugin provide some standard blocks for allowing IAuthenticatorPlugin
    templates to be interfaced with the layout/base
    """
    def template(self, settings, params):
        """
        Arguments:
        settings -- dict of key-value config specific to the plugin
        params -- a dict of values to be used within the template, typically
                  everything in the requests POST and GET, combined.

        Returns:
        a jinja2 template with blocks named 'title', 'head', and 'content'

        this template is referred to as "base.html" for extending/overriding
        purposes in IAuthenticatorPlugin templates
        """
        raise NotImplemented()


class IDataStorePlugin(IPlugin):
    """
    IDataStorePlugin's are used to interface with a data store of some type --
    for example: an authenticator needs to be able to generate a code and
    wait for a user to respond, so it needs to persist the request code for
    until a certain amount of time passes.
    """
    def initialize(self, settings):
        """
        Arguments:
        settings -- dict of key-value config specific to the plugin
        """
        raise NotImplemented()

    def store_access_request(self, subject, timestamp, payload):
        """
        deletes any outstanding access requests for subject

        Arguments:
        subject -- unique identity for the user/subject of the request
        payload -- string value that can be used to identify the access request later
        """
        raise NotImplemented()

    def get_access_request(self, subject):
        """
        Arguments:
        subject -- unique identity for the user/subject of the request

        Returns:
        only the latest request if more than one exist
        """
        raise NotImplemented()

    def delete_access_requests(self, subject):
        """
        deletes all access requests for the subject

        Arguments:
        subject -- unique identity for the user/subject of the request
        """
        raise NotImplemented()
