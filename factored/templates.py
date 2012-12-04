from pyramid.renderers import render


class TemplateRendererFactory(object):

    def __init__(self, req, context):
        self.context = context
        self.req = req

    def render(self, tmpl):
        try:
            return render(tmpl, self.context, request=self.req)
        except ValueError:
            return ''
