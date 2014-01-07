import os
from pyramid.httpexceptions import HTTPFound
import urllib
from factored.plugins import getFactoredPlugin, getFactoredPlugins
from factored.plugins import getPluginForRequest


class AuthView(object):

    def __init__(self, req):
        self.req = req
        self.plugin = getPluginForRequest(req)

    def __call__(self):
        return self.plugin.render()


def notfound(req):
    return HTTPFound(location="%s?%s" % (
        req.registry['settings']['base_auth_url'],
        urllib.urlencode({'referrer': req.url})))


def auth_chooser(req):
    auth_types = []
    settings = req.registry['settings']
    base_path = settings['base_auth_url']
    supported_types = settings['supported_auth_schemes']
    if len(supported_types) == 1:
        plugin = getFactoredPlugin(supported_types[0])
        referrer = urllib.urlencode(
            {'referrer': req.params.get('referrer', '')})
        raise HTTPFound(location="%s/%s?%s" % (base_path, plugin.path,
                                               referrer))
    for plugin in getFactoredPlugins():
        if plugin.name in supported_types:
            auth_types.append({
                'name': plugin.name,
                'url': os.path.join(base_path, plugin.path)
                })
    return dict(auth_types=auth_types,
                referrer=req.params.get('referrer', ''))
