from __future__ import absolute_import

from ..handlers import Handler
from openformats.strings import OpenString
from ..utils.compilers import OrderedCompilerMixin


class PlaintextHandler(OrderedCompilerMixin, Handler):
    name = "Plaintext"
    extension = "txt"

    def parse(self, content):
        stringset = []
        # find out whether we're using UNIX or DOS newlines
        try:
            position = content.index('\n')
        except ValueError:
            # No newlines present
            newline_sequence = ""
            lines = (content, )
        else:
            if position == 0 or content[position - 1] != '\r':
                newline_sequence = "\n"
            else:
                newline_sequence = "\r\n"
            lines = content.split(newline_sequence)

        template = ""
        order = 0
        for line in lines:
            stripped_line = line.strip()
            if stripped_line:
                string = OpenString(str(order), stripped_line, order=order)
                order += 1
                stringset.append(string)

                template_line = line.replace(stripped_line,
                                             string.template_replacement)
            template += newline_sequence
            if stripped_line:
                template += template_line
            else:
                template += line

        # remove newline_sequence added to the start of the template
        template = template[len(newline_sequence):]
        return template, stringset
