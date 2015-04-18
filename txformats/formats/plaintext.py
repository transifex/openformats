from __future__ import absolute_import

from ..handler import Handler, String
from ..utils.compilers import OrderedCompilerMixin
from ..utils.test import test_handler


class PlaintextHandler(OrderedCompilerMixin, Handler):
    name = "Plaintext"

    def feed_content(self, content):
        # find out whether we're using UNIX or DOS newlines
        try:
            position = content.index('\n')
        except ValueError:
            # No newlines present
            newline_sequence = ""
            line_generator = ((0, content), )
        else:
            if position == 0 or content[position - 1] != '\r':
                newline_sequence = "\n"
            else:
                newline_sequence = "\r\n"
            line_generator = enumerate(content.split(newline_sequence))

        template = ""
        for order, line in line_generator:
            stripped_line = line.strip()
            if stripped_line:
                string = String(str(order), stripped_line, order=order)
                yield string

                template_line = line.replace(stripped_line,
                                             string.template_replacement)
            template += newline_sequence
            if stripped_line:
                template += template_line
            else:
                template += line

        # remove newline_sequence added to the start of the template
        self.template = template[len(newline_sequence):]


def main():
    test_handler(PlaintextHandler, '''
        Hello world,

        My name is Kostas.
        How are you today?

        Regards,
        Kostas
    ''')


if __name__ == "__main__":
    main()
