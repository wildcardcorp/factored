from pyramid.events import subscriber
from pyramid.events import BeforeRender
from factored.templates import TemplateRendererFactory


@subscriber(BeforeRender)
def add_globals(event):
    req = event['request']
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
    if 'allow_code_reminder' not in context and 'selected-plugin' in req:
        context['allow_code_reminder'] = req['selected-plugin'].allow_code_reminder
    return context
