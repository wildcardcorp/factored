from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse

import jinja2
import jwt
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config

from factored.plugins import get_manager, get_plugin

from factored_manager.plugins.FactoredManagerEmailAuth import FactoredManagerEmailAuth

import logging
logger = logging.getLogger('factored.authenticator')
auditlog = logging.getLogger('factored.audit')

def generate_jwt(settings, subject):
    cname = settings.get("jwt.cookie.name", "factored")
    try:
        cage = int(settings.get("jwt.cookie.age", 24*60*60))
    except Exception:
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
    submit = req.params.get("submitbtn", None)
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
    host = req.domain
    reqsettings = req.registry.settings
    plugins = reqsettings.get("plugins.manager", None)
    if plugins is None:
        logger.error("plugin manager not configured")
        return Response(status_code=500)

    sp, sp_settings = get_plugin("plugins.settings", "settings", reqsettings, plugins)

    settings = {}
    settings.update(req.registry.settings)
    if sp is not None:
        settings.update(sp.plugin_object.get_request_settings(host))

    ds, ds_settings = get_plugin("plugins.datastore", "datastore", settings, plugins)
    finder, finder_settings = get_plugin("plugins.finder", "finder", settings, plugins)
    template, template_settings = get_plugin("plugins.template", "template", settings, plugins)
    registrar, registrar_settings = get_plugin("plugins.registrar", "registrar", settings, plugins)

    # get db
    if ds is None:
        logger.error("datastore not configured")
        return Response(status_code=500)
    else:
        ds = ds.plugin_object

    # get finder
    if finder is None:
        logger.error("finder not configured")
        return Response(status_code=500)
    else:
        finder = finder.plugin_object

    auth_type = get_authtype(req)

    authenticators = plugins.getPluginsOfCategory("authenticator")
    # authentication plugins activated:
    auth_options = [dict(value=a.name, display=a.plugin_object.display_name)
                    for a in authenticators]

    # grab default template data
    if template is None:
        logger.error("template not configured")
        return Response(status_code=500)
    base_tmpl_plugin = template
    base_tmpl_settings = template_settings
    base_tmpl_state = base_tmpl_plugin.plugin_object.state(host, base_tmpl_settings, req.params)
    base_tmpl_str = base_tmpl_plugin.plugin_object.template(base_tmpl_state, auth_options)

    # setup the jinja2 loader with the configured template info
    loader = {
        "base.html": base_tmpl_str,
    }
    tmpl_kwargs = {
        "state": base_tmpl_state,
        "auth_options": auth_options,
        "src": req.params.get("src", ""),
    }
    if auth_type is not None and auth_type.strip() != '':
        tmpl_kwargs["authtype"] = auth_type

    # if we have a valid auth type selected by the user, then get it's 
    # configured template info too
    tmpl = "base.html"
    if auth_type == "regform":
        if registrar is not None:
            registrar_tmpl_kwargs = registrar.plugin_object.handle(
                host,
                registrar_settings,
                req.params,
                ds,
                finder)
            tmpl_kwargs.update(registrar_tmpl_kwargs)
            registrar_tmpl_str = registrar.plugin_object.template(
                host,
                registrar_settings,
                req.params)
            tmpl = "registration.html"
            loader[tmpl] = registrar_tmpl_str

    elif auth_type is not None:
        auth_plugin, auth_tmpl_settings = get_plugin(auth_type, "authenticator", settings, plugins, nolookup=True)
        if auth_plugin is not None:
            auth_tmpl_kwargs = auth_plugin.plugin_object.handle(
                host,
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
                    auditlog.info('Successfully authenticated, redirecting now...')
                    src = urlparse(req.params.get("src", "/"))
                    goodsrc = (req.scheme, req.host, src.path, src.params, src.query, src.fragment)
                    resp.location = urlunparse(goodsrc)
                    resp.set_cookie(
                        name=cname,
                        value=enctoken,
                        max_age=cage,
                        secure=csec,
                        httponly=chttponly,
                        overwrite=True)
                    return FactoredManagerEmailAuth.modify_response(resp=resp, host=host, settings=settings, plugins=plugins, email=subject)
                tmpl_kwargs.update(auth_tmpl_kwargs)
            auth_tmpl_str = auth_plugin.plugin_object.template(host, auth_tmpl_settings, req.params)
            tmpl = "authtype.html"
            loader[tmpl] = auth_tmpl_str

    # render out the result of the base template + auth template
    tmpl_env = jinja2.Environment(
        loader=jinja2.DictLoader(loader),
        autoescape=jinja2.select_autoescape(['html', 'xml']))
    tmpl_rendered = tmpl_env.get_template(tmpl).render(**tmpl_kwargs)
    resp = Response(body=tmpl_rendered, status=200)
    return resp


def app(global_config, **settings):
    # setup the plugin manager
    plugindirs = settings.get('plugins.dirs', None)
    if plugindirs is not None:
        plugindirs = plugindirs.strip().splitlines()
    pluginmodules = settings.get('plugins.modules', None)
    if pluginmodules is not None:
        pluginmodules = pluginmodules.strip().splitlines()
    plugins = get_manager(plugin_dirs=plugindirs, plugin_modules=pluginmodules)
    settings["plugins.manager"] = plugins

    # setup the wsgi app
    config = Configurator(settings=settings)
    config.include('pyramid_mailer')
    config.add_route('authenticate', '/')
    config.scan('factored.authenticator')
    app = config.make_wsgi_app()
    return app
