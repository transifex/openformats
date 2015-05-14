import re

from ..handler import CopyMixin


class OrderedCompilerMixin(CopyMixin):
    SPACE_PAT = re.compile(r'^\s*$')

    def compile(self, template, stringset):
        # assume stringset is ordered within the template
        self.source = template
        self.destination = ""
        self.ptr = 0

        for string in stringset:
            hash_position = self.source.index(string.template_replacement)
            if not string.pluralized:
                self.copy_until(hash_position)
                self.add(string.string)
                self.skip(len(string.template_replacement))
            else:
                # if the hash is on its own on a line with only spaces, we have
                # to remember it's indent
                indent_length = self.source[hash_position::-1].index('\n') - 1
                indent = self.source[hash_position - indent_length:
                                     hash_position]
                tail_length = self.source[
                    hash_position + len(string.template_replacement):
                ].index('\n')
                tail = self.source[
                    hash_position + len(string.template_replacement):
                    hash_position + len(string.template_replacement) +
                    tail_length
                ]
                if (self.SPACE_PAT.search(indent) and
                        self.SPACE_PAT.search(tail)):
                    self.copy_until(hash_position - indent_length)
                    for rule, value in string.string.items():
                        self.add(
                            indent + self.plural_template.format(
                                rule=self.RULES_ITOA[rule], string=value
                            ) + tail + '\n'
                        )
                    self.skip(indent_length +
                              len(string.template_replacement) +
                              tail_length + 1)
                else:
                    # string is not on its own, simply replace hash with all
                    # plural forms
                    self.copy_until(hash_position)
                    for rule, value in string.string.items():
                        self.add(self.plural_template.format(
                            rule=self.RULES_ITOA[rule], string=value
                        ))
                    self.skip(len(string.template_replacement))

        self.copy_until(len(self.source))
        compiled = self.destination

        del self.source
        del self.destination
        del self.ptr

        return compiled

