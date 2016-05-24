import itertools

import polib

from ..handlers import Handler
from ..strings import OpenString


class PoHandler(Handler):
    name = "PO"
    extension = "po"
    EXTRACTS_RAW = False

    def parse(self, content):
        stringset = []
        order_gen = itertools.count()
        po = polib.pofile(content)
        for entry in po:
            string = OpenString(entry.msgid, entry.msgstr,
                                order=next(order_gen))
            entry.msgstr = string.template_replacement
            stringset.append(string)
        return unicode(po), stringset

    def compile(self, template, stringset):
        stringset = iter(stringset)
        next_string = next(stringset, None)

        po = polib.pofile(template)
        for entry in list(po):
            if (next_string is not None and
                    entry.msgstr == next_string.template_replacement):
                entry.msgstr = next_string.string
                next_string = next(stringset, None)
            else:
                po.remove(entry)
        return unicode(po)
