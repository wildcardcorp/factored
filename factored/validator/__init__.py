import jwt
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config

import logging
logger = logging.getLogger('factored.validator')
auditlog = logging.getLogger('factored.audit')

from factored.plugins import get_manager, get_plugin_settings


# req: request object with relevant identifying elements
# msg: string to log
# exc_info: True/False show exception info if found
# audit: True/False the message is getting logged to the audit log
def log_err(req, msg, exc_info=False, normal=True, audit=False):
    if normal:
        logger.error(msg, exc_info=exc_info)
    if audit:
        try:
            cookiename = req.registry.settings.get("jwt.cookie.name", "factored")
            token = req.cookies.get(cookiename, req.params.get("token", "<no jwt found>"))
            auditmsg = "{message} : {clientip} {jwttoken} {urlpath}".format(
                clientip=req.client_addr or "<no client ip set>",
                jwttoken=token,
                urlpath=req.path,
                message=msg)
            auditlog.error(auditmsg)
        except:
            logger.error("fatal error while logging to audit log")


def log_info(req, msg, exc_info=False, normal=True, audit=False):
    if normal:
        logger.info(msg, exc_info=exc_info)
    if audit:
        try:
            cookiename = req.registry.settings.get("jwt.cookie.name", "factored")
            token = req.cookies.get(cookiename, req.params.get("token", "<no jwt found>"))
            auditmsg = "{clientip} : {jwttoken} : {urlpath} : {message}".format(
                clientip=req.client_addr or "<no client ip set>",
                jwttoken=token,
                urlpath=req.path,
                message=msg)
            auditlog.info(auditmsg)
        except:
            logger.error("fatal error while logging to audit log")


#
# All this view is responsible for is validating that a JWT value is valid
# and that the subject it references is valid.
#
# IE the basic check would be that the token isn't expired and the subject is
# still an enabled/active user in the system (according to the configured
# finder plugin)
#
@view_config(route_name='validate')
def validate(req):
    host = req.host

    settings = {}
    settings.update(req.registry.settings)
    sp = settings.get("settingsplugin", None)
    if sp is not None:
        settings.update(sp.get_request_settings(host))

    # -- VALIDATE TOKEN
    cookiename = settings.get("jwt.cookie.name", "factored")
    enctoken = req.cookies.get(cookiename, None)
    if enctoken is None:
        # as a secondary, check to see if it was in the GET/POST as 'token'
        enctoken = req.params.get("token", None)
        if enctoken is None:
            # if not in a cookie, and not in the request, then no token :(
            log_info(req, "no token in request")
            return Response(status=403)

    audience = settings.get('jwt.audience', None)
    algo = settings.get('jwt.algorithm', 'HS512')
    secret = settings.get('jwt.secret', None)

    if audience is None:
        log_info(req, "audience not configured")
        return Response(status=403)
    if secret is None:
        log_info(req, "secret not configured")
        return Response(status=403)

    try:
        dectoken = jwt.decode(
            enctoken,
            secret,
            audience=audience,
            algorithms=[algo])
    except jwt.exceptions.ExpiredSignatureError:
        log_info(req, "expired signature", audit=True)
        return Response(status=403)
    except:
        log_err(req, "JWT Decode ERROR", exc_info=True, audit=True)
        return Response(status=403)

    subject = dectoken.get('sub', None)
    if subject is None:
        return Response(status=403)

    # -- VALIDATE TOKEN SUBJECT
    finder = settings["finder"].plugin_object
    if not finder.is_valid_subject(host, subject):
        msg = "{findername} : {subject} : not valid".format(
            findername=settings["finder"].name,
            subject=subject)
        log_info(req, msg, audit=True)
        return Response(status=403)

    log_info(req, "validated", normal=False, audit=True)
    return Response(status=200)


def app(global_config, **settings):
    # setup plugin manager
    plugindirs = settings.get('plugins.dirs', None)
    if plugindirs is not None:
        plugindirs = plugindirs.splitlines()
    pluginmodules = settings.get('plugins.modules', None)
    if pluginmodules is not None:
        pluginmodules = pluginmodules.splitlines()
    plugins = get_manager(plugin_dirs=plugindirs, plugin_modules=pluginmodules)
    settings["plugins.manager"] = plugins

    # setup finder
    findersettings = get_plugin_settings("plugins.finder", settings)
    findername = settings.get("plugins.finder", None)
    if findername is None:
        log_err(req, "finder plugin not configured")
        return None
    finder = plugins.getPluginByName(findername, category="finder")
    if finder is None:
        log_err(req, "finder plugin not found")
        return None
    finder.plugin_object.initialize(findersettings)
    settings["finder"] = finder

    # setup settings plugin
    sp_settings = get_plugin_settings("plugins.settings", settings)
    sp_name = settings.get("plugins.finder", None)
    sp_plugin = None
    if sp_name is not None and sp_name.strip() != "":
        sp_plugin = plugins.getPluginByName(sp_name, category="settings")
    settings["settingsplugin"] = sp_plugin

    # setup wsgi app
    config = Configurator(settings=settings)
    config.add_route('validate', '/')
    config.scan('factored.validator')
    app = config.make_wsgi_app()
    return app
