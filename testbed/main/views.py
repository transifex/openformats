from __future__ import absolute_import

import datetime
import inspect
import json
import os
import traceback
from importlib import import_module

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView, View
from django.views.generic.edit import CreateView

from openformats.handlers import Handler
from openformats.strings import OpenString

from .models import Payload


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
            for filename in os.listdir(os.path.join("openformats", "formats"))
            if filename.endswith(".py") and filename != "__init__.py"
        ]
        for filename in format_files:
            module = import_module("openformats.formats.{}".format(filename))
            for name, each in inspect.getmembers(module):
                if (inspect.isclass(each) and issubclass(each, Handler) and
                        each != Handler):
                    if each.name not in handlers:
                        handlers[each.name] = each
        return handlers


class MainView(HandlerMixin, TemplateView):
    http_method_names = ['get']
    template_name = "main/home.html"

    def get(self, request, payload_hash=""):
        self.payload_hash = payload_hash
        return super(MainView, self).get(request, payload_hash=payload_hash)

    def get_context_data(self, **kwargs):
        context = super(MainView, self).get_context_data(**kwargs)
        context['handlers'] = sorted(self.handlers.keys())
        if self.payload_hash:
            payload_row = get_object_or_404(Payload,
                                            payload_hash=self.payload_hash)
            payload_row.last_viewed = datetime.datetime.now()
            payload_row.save()
            context['payload_json'] = payload_row.payload
        return context


class ApiView(HandlerMixin, View):
    def post(self, request):
        payload = json.loads(request.body)
        if payload['action'] == "choose_handler":
            return_value = self._choose_handler(payload)
        elif payload['action'] == "parse":
            return_value = self._parse(payload)
        elif payload['action'] == "compile":
            return_value = self._compile(payload)
        return HttpResponse(json.dumps(return_value),
                            mimetype="application/json")

    def _choose_handler(self, payload):
        handler_name = payload['handler']
        handler_class = self.handlers[handler_name]
        handler_name_lower = handler_name.lower()
        sample_filepath = os.path.join(
            "openformats", "tests", "formats", handler_name_lower, "files",
            "1_en.{}".format(handler_class.extension)
        )
        return_value = {'handler': handler_name}
        try:
            with open(sample_filepath) as f:
                return_value['source'] = f.read()
        except IOError:
            pass
        return return_value

    def _parse(self, payload):
        handler_name = payload['handler']
        handler_class = self.handlers[handler_name]
        source = payload['source']

        handler = handler_class()
        returned_payload = {'action': None, 'compiled': "",
                            'compile_error': ""}
        try:
            template, stringset = handler.parse(source)
        except Exception:
            returned_payload.update({'stringset': [], 'template': "",
                                     'parse_error': traceback.format_exc()})
        else:
            returned_payload.update({
                'stringset': [self._string_to_json(string)
                              for string in stringset],
                'template': template,
                'parse_error': "",
            })

        return returned_payload

    def _string_to_json(self, string):
        return_value = {'id': string.template_replacement,
                        'key': string.key,
                        'strings': string._strings,
                        'pluralized': string.pluralized,
                        'template_replacement': string.template_replacement}
        for key in OpenString.DEFAULTS:
            return_value[key] = getattr(string, key)
        return return_value

    def _compile(self, payload):
        handler_name = payload['handler']
        handler_class = self.handlers[handler_name]
        stringset_json = payload['stringset']
        template = payload['template']

        stringset = []
        for string_json in stringset_json:
            key = string_json.pop('key')
            strings = {int(key): value
                       for key, value in string_json.pop('strings').items()}
            del string_json['pluralized']
            del string_json['template_replacement']
            stringset.append(OpenString(key, strings, **string_json))

        handler = handler_class()
        try:
            compiled = handler.compile(template, stringset)
        except Exception:
            returned_payload = {'action': None, 'compiled': "",
                                'compile_error': traceback.format_exc()}
        else:
            returned_payload = {'action': None, 'compiled': compiled,
                                'compile_error': ""}
        return returned_payload


class SaveView(CreateView):
    http_method_names = ['post']
    model = Payload

    def form_valid(self, form):
        try:
            return super(SaveView, self).form_valid(form)
        except Exception:
            return HttpResponseRedirect(form.instance.get_absolute_url())

    def form_invalid(self, form):
        return HttpResponseRedirect(form.instance.get_absolute_url())
