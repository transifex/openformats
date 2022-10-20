import itertools
import re

from fluent.syntax import ast, parse
from openformats.strings import OpenString
from openformats.transcribers import Transcriber
from openformats.utils.compilers import OrderedCompilerMixin

from ..handlers import Handler


class FluentHandler(OrderedCompilerMixin, Handler):
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
            string = OpenString(key, value, order=next(order))
            stringset.append(string)
            transcriber.copy_until(item.value.span.start)
            transcriber.add(string.template_replacement)
            transcriber.skip_until(item.value.span.end)
            for attribute in item.attributes:
                attribute_key = attribute.id.name
                value = source[attribute.value.span.start : attribute.value.span.end]
                string = OpenString(
                    ".".join((key, attribute_key)), value, order=next(order)
                )
                stringset.append(string)
                transcriber.copy_until(attribute.value.span.start)
                transcriber.add(string.template_replacement)
                transcriber.skip_until(attribute.value.span.end)
        transcriber.copy_to_end()
        return transcriber.get_destination(), stringset

    @staticmethod
    def unescape(string: str):
        lines = string.splitlines()
        if len(lines) > 1:
            indent = re.search("^\s*", lines[1]).end()
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
