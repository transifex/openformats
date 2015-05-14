import re

from ..handler import Transcriber


class OrderedCompilerMixin(object):
    SPACE_PAT = re.compile(r'^\s*$')

    def compile(self, template, stringset):
        # assume stringset is ordered within the template
        self.transcriber = Transcriber(template)

        for string in stringset:
            hash_position = template.index(string.template_replacement)
            if not string.pluralized:
                self.transcriber.copy_until(hash_position)
                self.transcriber.add(string.string)
                self.transcriber.skip(len(string.template_replacement))
            else:
                # if the hash is on its own on a line with only spaces, we have
                # to remember it's indent
                indent_length = template[hash_position::-1].index('\n') - 1
                indent = template[hash_position - indent_length:hash_position]
                tail_length = template[
                    hash_position + len(string.template_replacement):
                ].index('\n')
                tail = template[
                    hash_position + len(string.template_replacement):
                    hash_position + len(string.template_replacement) +
                    tail_length
                ]
                if (self.SPACE_PAT.search(indent) and
                        self.SPACE_PAT.search(tail)):
                    self.transcriber.copy_until(hash_position - indent_length)
                    for rule, value in string.string.items():
                        self.transcriber.add(
                            indent + self.plural_template.format(
                                rule=self.RULES_ITOA[rule], string=value
                            ) + tail + '\n'
                        )
                    self.transcriber.skip(indent_length +
                                          len(string.template_replacement) +
                                          tail_length + 1)
                else:
                    # string is not on its own, simply replace hash with all
                    # plural forms
                    self.transcriber.copy_until(hash_position)
                    for rule, value in string.string.items():
                        self.transcriber.add(self.plural_template.format(
                            rule=self.RULES_ITOA[rule], string=value
                        ))
                    self.transcriber.skip(len(string.template_replacement))

        self.transcriber.copy_until(len(template))
        compiled = self.transcriber.get_destination()

        return compiled
