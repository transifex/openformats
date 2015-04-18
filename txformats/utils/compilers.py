import re


class OrderedCompilerMixin(object):
    SPACE_PAT = re.compile(r'^\s*$')

    def compile(self, stringset):
        # assume stringset is ordered within the template
        compiled = ""
        template_ptr = 0
        for string in stringset:
            position = self.template.index(string.template_replacement)
            compiled += self.template[template_ptr:position]
            if not string.pluralized:
                compiled += string.string
                template_ptr = position + len(string.template_replacement)
            else:
                # if the hash is on its own on a line with only spaces, we have
                # to remember it's indent

                indent_length = self.template[position::-1].index('\n') - 1
                indent = self.template[position - indent_length:position]
                tail_length = self.template[
                    position + len(string.template_replacement):
                ].index('\n')
                tail = self.template[
                    position + len(string.template_replacement):
                    position + len(string.template_replacement) + tail_length
                ]

                if (self.SPACE_PAT.search(indent) and
                        self.SPACE_PAT.search(tail)):
                    compiled = compiled[:len(compiled) - indent_length]
                    for rule, value in string.string.items():
                        compiled += indent +\
                            self.plural_template.format(
                                rule=self.RULES_ITOA[rule], string=value
                            ) +\
                            tail + "\n"
                    template_ptr = position +\
                        len(string.template_replacement) + tail_length + 1
                else:
                    # string is not on its own, simply replace hash with all
                    # plural forms

                    compiled += self.template[template_ptr:position]
                    for rule, value in string.string.items():
                        compiled += self.plural_template.format(
                            rule=self.RULES_ITOA[rule], string=value
                        )
                    template_ptr = position + len(string.template_replacement)

        compiled += self.template[template_ptr:]
        return compiled
