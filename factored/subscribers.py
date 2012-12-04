from pyramid.events import subscriber
from pyramid.events import BeforeRender
from factored.templates import TemplateRendererFactory


@subscriber(BeforeRender)
def add_globals(event):
    req = event['request']
    view = event['view']
    context = event.rendering_val
    if 'static_path' not in context:
        context['static_path'] = req.registry['settings']['static_path']
    if 'req' not in context:
        context['req'] = req
    if 'templates' not in context:
        templates = TemplateRendererFactory(req, context)
        context['templates'] = templates
        def render(name):
            return templates.render('templates/%s' % name)
        context['render'] = render
    if 'content_renderer' not in context:
        context['content_renderer'] = 'templates/auth-chooser.pt'
    return context