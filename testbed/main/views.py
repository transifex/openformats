import inspect
import os
from importlib import import_module

from django.views.generic.base import TemplateView

from txformats.handler import Handler


class MainView(TemplateView):
    template_name = "main/home.html"

    def get_context_data(self, **kwargs):
        context = super(MainView, self).get_context_data(**kwargs)
        context['handlers'] = sorted(self.handlers.keys())
        return context

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
