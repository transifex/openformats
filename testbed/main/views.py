import inspect
import json
import os
from importlib import import_module

from django.http import HttpResponse
from django.views.generic.base import TemplateView, View

from txformats.handler import Handler


class HandlerMixin(object):
    @property
    def handlers(self):
        if not hasattr(self, "_handlers"):
            self._handlers = self._get_handlers()
        return self._handlers

    def _get_handlers(self):
        handlers = {}
        format_files = [
            filename.split(".")[0]
            for filename in os.listdir(os.path.join("txformats", "formats"))
            if filename.endswith(".py") and filename != "__init__.py"
        ]
        for filename in format_files:
            module = import_module("txformats.formats.{}".format(filename))
            for name, each in inspect.getmembers(module):
                if (inspect.isclass(each) and issubclass(each, Handler) and
                        each != Handler):
                    if each.name not in handlers:
                        handlers[each.name] = each
        return handlers


class MainView(HandlerMixin, TemplateView):
    template_name = "main/home.html"

    def get_context_data(self, **kwargs):
        context = super(MainView, self).get_context_data(**kwargs)
        context['handlers'] = sorted(self.handlers.keys())
        return context


class ApiView(HandlerMixin, View):
    def post(self, request):
        payload = json.loads(request.body)
        if payload['action'] == "parse":
            return self._parse(payload)

    def _parse(self, payload):
        handler_name = payload['handler']
        handler_class = self.handlers[handler_name]
        source = payload['source']

        handler = handler_class()
        stringset = list(handler.feed_content(source))
        template = handler.template
        del payload['action']
        payload['stringset'] = [str(string) for string in stringset]
        payload['template'] = template

        return HttpResponse(json.dumps(payload), mimetype="application/json")
