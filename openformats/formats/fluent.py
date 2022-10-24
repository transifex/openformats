import itertools
import re

from fluent.syntax import ast, parse
from openformats.strings import OpenString
from openformats.transcribers import Transcriber

from ..handlers import Handler


class FluentHandler(Handler):
    # https://projectfluent.org/
    name = "FLUENT"
    extension = "ftl"
    EXTRACTS_RAW = True

    def parse(self, source, is_source=False):
        transcriber = Transcriber(source)
        source = transcriber.source
        parsed = parse(source)
        stringset = []
        order = itertools.count()
        for item in parsed.body:
            if not isinstance(item, (ast.Message, ast.Term)):
                continue
            key = item.id.name
            value = source[item.value.span.start : item.value.span.end]
            indent = re.search(r"^\s*", value).end()
            rest = value[indent:]
            string = OpenString(key, rest, order=next(order))
            stringset.append(string)
            transcriber.copy_until(item.value.span.start + indent)
            transcriber.add(string.template_replacement)
            transcriber.skip_until(item.value.span.end)
            for attribute in item.attributes:
                attribute_key = attribute.id.name
                value = source[attribute.value.span.start : attribute.value.span.end]
                indent = re.search(r"^\s*", value).end()
                rest = value[indent:]
                string = OpenString(
                    ".".join((key, attribute_key)), rest, order=next(order)
                )
                stringset.append(string)
                transcriber.copy_until(attribute.value.span.start + indent)
                transcriber.add(string.template_replacement)
                transcriber.skip_until(attribute.value.span.end)
        transcriber.copy_to_end()
        return transcriber.get_destination(), stringset

    def compile(self, template, stringset, **kwargs):
        transcriber = Transcriber(template)
        template = transcriber.source
        parsed = parse(template)
        stringset = iter(stringset)
        next_string = next(stringset, None)
        delete = False
        for item in parsed.body:
            transcriber.copy_until(item.span.start)
            transcriber.mark_section_end()
            if delete:
                transcriber.remove_section()
                delete = False
            if not isinstance(item, (ast.Message, ast.Term)):
                continue
            transcriber.mark_section_start()
            value = template[item.value.span.start : item.value.span.end]
            indent = re.search(r"^\s*", value).end()
            rest = value[indent:]
            if next_string is not None and rest == next_string.template_replacement:
                transcriber.copy_until(item.value.span.start + indent)
                transcriber.add(next_string.string)
                next_string = next(stringset, None)
                transcriber.skip_until(item.value.span.end)
            else:
                delete = True
            for attribute in item.attributes:
                value = template[attribute.value.span.start : attribute.value.span.end]
                indent = re.search(r"^\s*", value).end()
                rest = value[indent:]
                if next_string is not None and rest == next_string.template_replacement:
                    transcriber.copy_until(attribute.value.span.start + indent)
                    transcriber.add(next_string.string)
                    next_string = next(stringset, None)
                    transcriber.skip_until(attribute.value.span.end)
                else:
                    transcriber.copy_until(attribute.span.start)
                    transcriber.skip_until(attribute.span.end)
                # else: delete segment
        transcriber.copy_to_end()
        transcriber.mark_section_end()
        if delete:
            transcriber.remove_section()
        return transcriber.get_destination()

    @staticmethod
    def unescape(string: str):
        lines = string.splitlines()
        if len(lines) > 1:
            indent = re.search(r"^\s*", lines[1]).end()
            result = [lines[0].strip()]
            for line in lines[1:]:
                if not line[:indent].isspace():
                    return string
                result.append(line[indent:].strip())
            return " ".join(result)
        else:
            return string

    @staticmethod
    def escape(string):
        return string
