from pyramid.events import subscriber
from pyramid.events import BeforeRender
from factored.templates import TemplateRendererFactory


@subscriber(BeforeRender)
def add_globals(event):
    req = event['request']
    view = event['view']
    context = event.rendering_val
    if context is None:
        return {}
    if 'static_path' not in context:
        context['static_path'] = req.registry['settings']['static_path']
    if 'req' not in context:
        context['req'] = req
    if 'templates' not in context:
        templates = TemplateRendererFactory(req, context)
        context['templates'] = templates

        def render(name):
            if ':' in name:
                return templates.render(name)
            else:
                return templates.render('templates/%s' % name)
        context['render'] = render
    if 'content_renderer' not in context:
        context['content_renderer'] = 'templates/auth-chooser.pt'
    if 'allow_code_reminder' not in context:
        if hasattr(view, 'allow_code_reminder'):
            context['allow_code_reminder'] = view.allow_code_reminder
        elif 'auth_plugin' in context:
            context['allow_code_reminder'] = \
                context['auth_plugin'].allow_code_reminder
    # update app settings as template globals. Only missing ones.
    for key, value in req.registry['settings'].items():
        if key not in context:
            context[key] = value
    return context
