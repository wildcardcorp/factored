import jwt
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config

from factored.plugins import get_manager, get_plugin

import logging
logger = logging.getLogger('factored.validator')
auditlog = logging.getLogger('factored.audit')


# req: request object with relevant identifying elements
# msg: string to log
# exc_info: True/False show exception info if found
# audit: True/False the message is getting logged to the audit log
def log_err(req, msg, subject=None, exc_info=False, normal=True, audit=False):
    if normal:
        logger.error(msg, exc_info=exc_info)
    if audit:
        try:
            cookiename = req.registry.settings.get("jwt.cookie.name", "factored")
            token = req.cookies.get(cookiename, req.params.get("token", "<unknown>"))
            subject = subject if subject is not None else token
            auditmsg = "{message} : {clientip} {subject} {urlpath}".format(
                clientip=req.client_addr or "<no client ip set>",
                subject=subject,
                urlpath=req.path,
                message=msg)
            auditlog.error(auditmsg)
        except Exception:
            logger.error("fatal error while logging to audit log")


def log_info(req, msg, subject=None, exc_info=False, normal=True, audit=False):
    if normal:
        logger.info(msg, exc_info=exc_info)
    if audit:
        try:
            cookiename = req.registry.settings.get("jwt.cookie.name", "factored")
            token = req.cookies.get(cookiename, req.params.get("token", "<unknown>"))
            subject = subject if subject is not None else token
            auditmsg = "{clientip} : {subject} : {urlpath} : {message}".format(
                clientip=req.client_addr or "<no client ip set>",
                subject=subject,
                urlpath=req.path,
                message=msg)
            auditlog.info(auditmsg)
        except Exception:
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
    host = req.domain
    reqsettings = req.registry.settings
    plugin_manager = reqsettings.get("plugins.manager", None)
    if plugin_manager is None:
        log_err(req, "plugin manager not configured")
        return Response(status=500)

    sp, sp_settings = get_plugin("plugins.settings", "settings", reqsettings, plugin_manager)

    settings = {}
    settings.update(req.registry.settings)
    if sp is not None:
        settings.update(sp.plugin_object.get_request_settings(host))

    finder, finder_settings = get_plugin("plugins.finder", "finder", settings, plugin_manager)

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
    except Exception:
        log_err(req, "JWT Decode ERROR", exc_info=True, audit=True)
        return Response(status=403)

    subject = dectoken.get('sub', None)
    if subject is None:
        return Response(status=403)

    # -- VALIDATE TOKEN SUBJECT
    if not finder.plugin_object.is_valid_subject(host, subject):
        msg = "{findername} : {subject} : not valid".format(
            findername=finder.name,
            subject=subject)
        log_info(req, msg, audit=True)
        return Response(status=403)

    log_info(req, "validated", normal=False, audit=True)
    return Response(status=200)


@view_config(route_name='status')
def status(req):
    # check that we can get the plugin manager
    host = req.domain
    reqsettings = req.registry.settings
    plugin_manager = reqsettings.get("plugins.manager", None)
    if plugin_manager is None:
        log_err(req, "plugin manager not configured")
        return Response(status=500)

    # check that we can get all the appropriate settings
    sp, _ = get_plugin("plugins.settings", "settings", reqsettings, plugin_manager)
    settings = {}
    settings.update(req.registry.settings)
    if sp is None:
        log_err(req, "no settings plugin found")
        return Response(status=500)
    else:
        try:
            settings.update(sp.plugin_object.get_request_settings(host))
        except Exception:
            log_err(req, "couldn't fetch settings through settings plugin", exc_info=True)
            return Response(status=500)

    # check we can get the finder
    finder, _ = get_plugin("plugins.finder", "finder", settings, plugin_manager)
    if finder is None:
        log_err(req, "no finder plugin found")
        return Response(status=500)
    else:
        try:
            # don't care if it's valid or not, just that it executes without exception
            finder.plugin_object.is_valid_subject(host, "__notarealsubject__")
        except Exception:
            log_err(req, "problem checking subject validity", exc_info=True)
            return Response(status=500)

    return Response(status=200)


def app(global_config, **settings):
    # setup plugin manager
    plugindirs = settings.get('plugins.dirs', None)
    if plugindirs is not None:
        plugindirs = plugindirs.strip().splitlines()
    pluginmodules = settings.get('plugins.modules', None)
    if pluginmodules is not None:
        pluginmodules = pluginmodules.strip().splitlines()
    plugins = get_manager(plugin_dirs=plugindirs, plugin_modules=pluginmodules)
    settings["plugins.manager"] = plugins

    # setup wsgi app
    config = Configurator(settings=settings)
    config.add_route('validate', '/')
    config.add_route('status', '/validator-status')
    config.scan('factored.validator')
    app = config.make_wsgi_app()
    return app
