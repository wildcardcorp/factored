import os
from pyramid.httpexceptions import HTTPFound
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
from factored.plugins import getFactoredPlugin, getFactoredPlugins
from factored.plugins import getPluginForRequest
from factored.utils import generate_url


class AuthView(object):

    def __init__(self, req):
        self.req = req
        self.plugin = getPluginForRequest(req)

    def __call__(self):
        return self.plugin.render()


def notfound(req):
    base_path = req.registry['settings']['base_auth_url']
    orig_url = generate_url(req, req.path)
    redirect_url = generate_url(
        req,
        base_path,
        params=dict(referrer=orig_url))
    return HTTPFound(location=redirect_url)


def auth_chooser(req):
    auth_types = []
    settings = req.registry['settings']
    base_path = settings['base_auth_url']
    supported_types = settings['supported_auth_schemes']
    if len(supported_types) == 1:
        plugin = getFactoredPlugin(supported_types[0])
        url = generate_url(req, base_path + '/' + plugin.path,
                           {'referrer': req.params.get('referrer', '')})
        raise HTTPFound(location=url)

    for plugin in getFactoredPlugins():
        if plugin.name in supported_types:
            auth_types.append({
                'name': plugin.name,
                'url': os.path.join(base_path, plugin.path)
                })
    return dict(auth_types=auth_types,
                referrer=req.params.get('referrer', ''))
