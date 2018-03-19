import importlib
import os
from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManager
from yapsy.PluginFileLocator import PluginFileLocator
from yapsy.PluginFileLocator import PluginFileAnalyzerMathingRegex
from yapsy.PluginInfo import PluginInfo

import logging
logger = logging.getLogger("factored.plugins")


def get_manager(plugin_dirs=None, plugin_modules=None, load_defaults=True):
    """
    Keyword Arguments:
    plugin_dirs -- list of directory paths where plugins should be searched for
    plugin_modules -- list of strings representing the dotted path of a python module
    load_defaults -- True to load the plugins included with factored

    Returns:
    A yapsy.PluginManager.PluginManager instance with all configured plugins loaded
    """
    if plugin_dirs is None or type(plugin_dirs) is not list:
        plugin_dirs = []
    if plugin_modules is None or type(plugin_modules) is not list:
        plugin_modules = []

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
        "settings": ISettingsPlugin,
    })
    manager.locatePlugins()

    if len(plugin_modules) > 0:
        for dname in plugin_modules:
            module = importlib.import_module(dname)
            pname = dname.split(".")[-1]
            infopath = module.__file__[:-3]
            infoobj = PluginInfo(pname, infopath)
            candidate = (infopath, module.__file__, infoobj)
            manager.appendPluginCandidate(candidate)


    manager.loadPlugins()
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
                settings for the plugin, otherwise the name_setting will be used
                to look up the name of the plugin to use in the defult prefix
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


def get_plugin(name_setting, category, allsettings, plugin_manager, nolookup=False):
    """
    Arguments:
    name_setting -- name of setting that the plugin name is specified in, IE
                    name of setting might be "plugins.finder" and plugin name
                    might be "EMailDomain"
    allsettings -- the complete set of settings to use for plugin configuration

    Keyword Arguments:
    nolookup -- if True then name_setting will be the prefix to use to find all
                settings for the plugin, otherwise the name_setting will be used
                to look up the name of the plugin to use in the defult prefix

    Returns:
    2-tuple with the first element being the PluginInfo object and the second
    being a dict of settings for the plugin.
    """

    # nolookup?
    #   - TRUE:
    #       - plugin == name_setting
    #       - settings == plugins.<name_setting>.*
    #   - FALSE:
    #       - plugin == settings[name_setting]
    #       - settings == plugins.<settings[name_setting]>.*

    if nolookup:
        p_name = name_setting
        p_settings_name = "plugin.{}.".format(p_name)
    else:
        p_name = allsettings.get(name_setting, None)
        if p_name is None:
            return (None, None)
        p_settings_name = name_setting

    p_settings = get_plugin_settings(p_settings_name, allsettings, nolookup=nolookup)
    p = plugin_manager.getPluginByName(p_name, category=category)
    return (p, p_settings)


class IFinderPlugin(IPlugin):
    """
    IFinderPlugin's are used primarily in the factored.validator for the express
    purpose of approving or denying the subject of a given token
    """

    def initialize(self, settings):
        """
        Arguments:
        settings -- dict of key-value config specific to the plugin
        """
        raise NotImplemented()

    def is_valid_subject(self, host, sub):
        """
        Arguments:
        host -- the host the request is being made too
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

    def handle(self, host, settings, params, datastore, finder):
        """
        Arguments:
        host -- the host the request is being made too
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

    def template(self, host, settings, params):
        """
        Arguments:
        host -- the host the request is being made too
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
    def handle(self, host, settings, params, datastore, finder):
        """
        Arguments:
        host -- the host the request is being made too
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

    def template(self, host, settings, params):
        """
        Arguments:
        host -- the host the request is being made too
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
    def state(self, host, settings, params):
        """
        Given the app settings and request params, return a state this template
        is in.

        Arguments:
        host -- the host the request is being made too
        settings -- dict of key-value config specific to the plugin
        params -- a dict of values to be used within the template, typically
                  everything in the requests POST and GET, combined.
        """
        raise NotImplemented()

    def template(self, state, auth_options):
        """
        Arguments:
        state -- dict containing output of the state() function. This value
                 should also be available to the template when being rendered.
        auth_options -- a list of dict's containing 'display' and 'value'
                        members that describe possible authentication options
                        available. This value should also be available to the
                        template when being rendered.

        Returns:
        an (unrendered) jinja2 template

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

    def store_access_request(self, host, subject, timestamp, payload):
        """
        deletes any outstanding access requests for subject

        Arguments:
        host -- the host the request is being made too
        subject -- unique identity for the user/subject of the request
        payload -- string value that can be used to identify the access request later
        """
        raise NotImplemented()

    def get_access_request(self, host, subject):
        """
        Arguments:
        host -- the host the request is being made too
        subject -- unique identity for the user/subject of the request

        Returns:
        only the latest request if more than one exist
        """
        raise NotImplemented()

    def delete_access_requests(self, host, subject):
        """
        deletes all access requests for the subject

        Arguments:
        host -- the host the request is being made too
        subject -- unique identity for the user/subject of the request
        """
        raise NotImplemented()


class ISettingsPlugin(IPlugin):
    """
    ISettingsPlugin's are used by augment other plugin's settings on a
    per-request basis.
    """
    def get_request_settings(self, host):
        """
        Arguments:
        host -- the host the request is being made too

        Returns:
        a dict (empty or otherwise) of all settings that should take priority
        for a request. They are applied over and along side the app settings
        every request.
        """
        raise NotImplemented()
