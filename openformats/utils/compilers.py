import re

import six

from openformats.transcribers import Transcriber
from openformats.utils.compat import ensure_unicode


class OrderedCompilerMixin(object):
    SPACE_PAT = r'^\s*$'

    def compile(self, template, stringset, **kwargs):
        # Fix regex encoding
        space_pattern = re.compile(ensure_unicode(self.SPACE_PAT))

        # assume stringset is ordered within the template
        transcriber = Transcriber(template)
        template = transcriber.source

        for string in stringset:
            hash_position = template.index(string.template_replacement)
            if not string.pluralized:
                transcriber.copy_until(hash_position)
                transcriber.add(string.string)
                transcriber.skip(len(string.template_replacement))
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
                if (space_pattern.search(indent) and
                        space_pattern.search(tail)):
                    transcriber.copy_until(hash_position - indent_length)
                    for rule, value in six.iteritems(string.string):
                        transcriber.add(
                            indent + self.plural_template.format(
                                rule=self.RULES_ITOA[rule], string=value
                            ) + tail + '\n'
                        )
                    transcriber.skip(indent_length +
                                     len(string.template_replacement) +
                                     tail_length + 1)
                else:
                    # string is not on its own, simply replace hash with all
                    # plural forms
                    transcriber.copy_until(hash_position)
                    for rule, value in six.iteritems(string.string):
                        transcriber.add(self.plural_template.format(
                            rule=self.RULES_ITOA[rule], string=value
                        ))
                    transcriber.skip(len(string.template_replacement))

        transcriber.copy_until(len(template))
        compiled = transcriber.get_destination()

        return compiled
