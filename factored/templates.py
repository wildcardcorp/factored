from pyramid.renderers import render
from factored import TEMPLATE_CUSTOMIZATIONS
import os
from pyramid.path import package_path


def registerTemplateCustomizations(config, _dir, package):
    registry = config.registry
    if TEMPLATE_CUSTOMIZATIONS not in registry:
        registry[TEMPLATE_CUSTOMIZATIONS] = {}
    path = os.path.join(package_path(package), _dir)
    for fi in os.listdir(path):
        registry[TEMPLATE_CUSTOMIZATIONS][fi] = (
            package, os.path.join(_dir, fi))


class TemplateRendererFactory(object):

    def __init__(self, req, context):
        self.context = context
        self.req = req
        self.customizations = req.registry[TEMPLATE_CUSTOMIZATIONS]
        if not self.customizations and 'app' in req.registry:
            try:
                self.customizations = self.req.registry['app'].app.config.registry[TEMPLATE_CUSTOMIZATIONS]  # noqa
            except:
                pass

    def render(self, tmpl, package=None):
        try:
            tmpl_name = os.path.basename(tmpl)
            if tmpl_name in self.customizations:
                package, tmpl = self.customizations[tmpl_name]
            if package is None and ':' in tmpl:
                pkg, tmpl = tmpl.split(':', 1)
                try:
                    package = __import__(pkg)
                except ImportError:
                    pass
            return render(tmpl, self.context, request=self.req,
                          package=package)
        except ValueError:
            return ''
