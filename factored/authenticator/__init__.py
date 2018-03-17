from datetime import datetime, timedelta
import jinja2
import jwt
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config

import logging
logger = logging.getLogger('factored.authenticator')

from factored.plugins import get_manager, get_plugin_settings


def generate_jwt(settings, subject):
    cname = settings.get("jwt.cookie.name", "factored")
    try:
        cage = int(settings.get("jwt.cookie.age", 24*60*60))
    except:
        logger.error("error reading jwt.cookie.age from settings")
        cage = 24*60*60
    csec = settings.get("jwt.cookie.secure", "true").strip().lower() == "true"
    chttponly = settings.get("jwt.cookie.httponly", "true").strip().lower() == "true"

    audience = settings.get('jwt.audience', None)
    algo = settings.get('jwt.algorithm', 'HS512')
    secret = settings.get('jwt.secret', None)
    exp = datetime.utcnow() + timedelta(seconds=cage)
    enctoken = jwt.encode(
        dict(
            sub=subject,
            exp=exp,
            aud=audience,
        ),
        secret,
        algorithm=algo)

    return (cname, cage, csec, chttponly, enctoken)


def get_authtype(req):
    # auth_type is derived from either the auth options submit button, or
    # the normal form submission (hidden value)
    submit = req.params.get("submit", None)
    if submit is not None:
        if submit.startswith("authtype_"):
            auth_type = submit[9:]
        else:
            auth_type = req.params.get("authtype", None)
    else:
        auth_type = req.params.get("authtype", None)

    return auth_type


@view_config(route_name='authenticate')
def authenticate(req):
    settings = req.registry.settings

    # get db
    ds = settings.get("datastore", None)
    if ds is None:
        logger.error("datastore not configured")
        return Response(status_code=500)
    else:
        ds = ds.plugin_object

    # get finder
    finder = settings.get("finder", None)
    if finder is None:
        logger.error("finder not configured")
        return Response(status_code=500)
    else:
        finder = finder.plugin_object

    auth_type = get_authtype(req)

    plugins = settings["plugins.manager"]
    authenticators = plugins.getPluginsOfCategory("authenticator")

    # grab default template data
    templatename = settings.get("plugins.template", "DefaultTemplate")
    base_tmpl_plugin = plugins.getPluginByName(templatename, category="template")
    base_tmpl_settings = settings.get("templatesettings", {})
    base_tmpl_state = base_tmpl_plugin.plugin_object.state(base_tmpl_settings, req.params)
    base_tmpl_str = base_tmpl_plugin.plugin_object.template(base_tmpl_settings, req.params)

    # setup the jinja2 loader with the configured template info
    loader = {
        "base.html": base_tmpl_str,
    }
    tmpl_kwargs = {
        "state": base_tmpl_state,
        "auth_options": [dict(value=a.name, display=a.plugin_object.display_name)
                         for a in authenticators],
        "src": req.params.get("src", ""),
    }
    if auth_type is not None:
        tmpl_kwargs["authtype"] = auth_type

    # if we have a valid auth type selected by the user, then get it's 
    # configured template info too
    tmpl = "base.html"
    if auth_type is not None and auth_type == "regform":
        registrar = settings.get("registrar", None)
        if registrar is not None:
            registrar_settings = settings.get("registrarsettings", {})
            registrar_tmpl_kwargs = registrar.plugin_object.handle(
                registrar_settings,
                req.params,
                ds,
                finder)
            tmpl_kwargs.update(registrar_tmpl_kwargs)
            registrar_tmpl_str = registrar.plugin_object.template(
                registrar_settings,
                req.params)
            tmpl = "registration.html"
            loader[tmpl] = registrar_tmpl_str

    elif auth_type is not None:
        auth_plugin = plugins.getPluginByName(auth_type, category="authenticator")
        if auth_plugin is not None:
            auth_tmpl_settings = get_plugin_settings("plugin.{}.".format(auth_type), settings, nolookup=True)
            auth_tmpl_kwargs = auth_plugin.plugin_object.handle(
                auth_tmpl_settings,
                req.params,
                ds,
                finder)
            if auth_tmpl_kwargs is not None:
                subject = auth_tmpl_kwargs.get("subject", None)
                authenticated = auth_tmpl_kwargs.get("authenticated", False)
                # SUCCESSFULLY AUTHENTICATED
                if authenticated and subject is not None:
                    cname, cage, csec, chttponly, enctoken = generate_jwt(settings, subject)
                    resp = Response(
                        body="Successfully authenticated, redirecting now...",
                        status=302)
                    resp.location = req.params.get("src", "/")
                    resp.set_cookie(
                        name=cname,
                        value=enctoken,
                        max_age=cage,
                        secure=csec,
                        httponly=chttponly,
                        overwrite=True)
                    return resp
                tmpl_kwargs.update(auth_tmpl_kwargs)
            auth_tmpl_str = auth_plugin.plugin_object.template(auth_tmpl_settings, req.params)
            tmpl = "authtype.html"
            loader[tmpl] = auth_tmpl_str

    # render out the result of the base template + auth template
    tmpl_env = jinja2.Environment(
        loader=jinja2.DictLoader(loader),
        autoescape=jinja2.select_autoescape(['html', 'xml']))
    tmpl_rendered = tmpl_env.get_template(tmpl).render(**tmpl_kwargs)

    return Response(body=tmpl_rendered, status=200)


def app(global_config, **settings):
    # setup the plugin manager
    plugindirs = settings.get('plugins.dirs', None)
    if plugindirs is not None:
        plugindirs = plugindirs.splitlines()
    pluginmodules = settings.get('plugins.modules', None)
    if pluginmodules is not None:
        pluginmodules = pluginmodules.splitlines()
    plugins = get_manager(plugin_dirs=plugindirs, plugin_modules=pluginmodules)
    settings["plugins.manager"] = plugins

    # store the configured root template's settings here so it doesn't need
    # to be re-done every request
    settings["templatesettings"] = get_plugin_settings("plugins.template", settings)

    # setup the configured datastore
    dspluginname = settings.get("plugins.datastore", "SQLDataStore")
    dspluginsettings = get_plugin_settings("plugins.datastore", settings)
    ds = plugins.getPluginByName(dspluginname, category="datastore")
    ds.plugin_object.initialize(dspluginsettings)
    settings["datastore"] = ds

    # setup the configured finder
    finderpluginname = settings.get("plugins.finder", None)
    if not finderpluginname:
        logger.error("plugins.finder not configured")
        return None
    finderpluginsettings = get_plugin_settings("plugins.finder", settings)
    settings["findersettings"] = finderpluginsettings
    finder = plugins.getPluginByName(finderpluginname, category="finder")
    finder.plugin_object.initialize(finderpluginsettings)
    settings["finder"] = finder

    # setup the configured registrar
    registrarpluginname = settings.get("plugins.registrar", None)
    if not registrarpluginname:
        logger.info("plugins.registrar not configured")
    else:
        registrarpluginsettings = get_plugin_settings("plugins.registrar", settings)
        settings["registrarsettings"] = registrarpluginsettings
        registrar = plugins.getPluginByName(registrarpluginname, category="registrar")
        settings["registrar"] = registrar

    # setup the wsgi app
    config = Configurator(settings=settings)
    config.include('pyramid_mailer')
    config.add_route('authenticate', '/')
    config.scan('factored.authenticator')
    app = config.make_wsgi_app()
    return app
