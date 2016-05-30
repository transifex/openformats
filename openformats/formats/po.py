import itertools

import polib

from ..handlers import Handler
from ..strings import OpenString
from ..exceptions import ParseError


class PoHandler(Handler):
    name = "PO"
    extension = "po"

    FUZZY_FLAG = 'fuzzy'
    EXTRACTS_RAW = False

    def parse(self, content):
        stringset = []
        self.order_generator = itertools.count()
        self.po = polib.pofile(content)
        for entry in self.po:
            openstring = self._handle_entry(entry)
            if openstring is not None:
                stringset.append(openstring)
        return unicode(self.po), stringset

    def _handle_entry(self, entry):
        entry_key, string, pluralized = self._get_string_data(entry)
        if string is not None:
            openstring_kwargs = {'pluralized': pluralized}
            # Check fuzziness
            if self.FUZZY_FLAG in entry.flags:
                # If fuzzy create flag and remove from template
                openstring_kwargs['fuzzy'] = True
                self.po.remove(entry)
            else:
                openstring_kwargs['order'] = next(self.order_generator)
            return self._create_openstring(
                entry, entry_key, string, openstring_kwargs
            )
        # If string is empty
        self.po.remove(entry)
        return None

    def _get_string_data(self, entry):
        entry_key, pluralized = self._get_key_and_plural(entry)
        if pluralized:
            if entry.msgstr.strip():
                raise ParseError(entry_key)
            string = entry.msgstr_plural
        else:
            if entry.msgstr_plural:
                raise ParseError(entry_key)
            string = entry.msgstr
        not_empty = self._validate_not_empty(entry, string, pluralized)
        if not_empty:
            return entry_key, string, pluralized
        return None, None, None

    def _get_key_and_plural(self, entry):
        # Get format keys to avoid colisions
        key = entry.msgid.strip().replace(
            '\\', '\\\\'
        ).replace(':', '\\:')
        plural_key = entry.msgid_plural.strip().replace(
            '\\', '\\\\'
        ).replace(':', '\\:')
        if not key:
            raise ParseError(u"Found empty msgid")

        if plural_key:
            pluralized = True
            entry_key = ':'.join([key, plural_key])
        else:
            pluralized = False
            entry_key = key
        return entry_key, pluralized

    def _validate_not_empty(self, entry, string, pluralized):
        if not string:
            return False
        elif pluralized:
            # Find the plurals that have empty string
            text_value_set = set(
                value and value.strip() or "" for value in string.itervalues()
            )
            if "" in text_value_set and len(text_value_set) != 1:
                # If not all plurals have empty strings raise ParseError
                msg = (
                    u"Incomplete plurals found on string with msgid `{}` "
                    u"and msgid_plural `{}`".format(
                        entry.msgid, entry.msgid_plural
                    )
                )
                raise ParseError(msg)
            elif "" in text_value_set:
                # All plurals are empty so skip `plurals` tag
                return False
        elif string.strip() == "":
            return False
        return True

    def _create_openstring(self, entry, entry_key, string, openstring_kwargs):
        openstring = OpenString(
            entry_key,
            string,
            **openstring_kwargs
        )
        if not openstring_kwargs['pluralized']:
            entry.msgstr = openstring.template_replacement
        else:
            entry.msgstr_plural = {'0': openstring.template_replacement}
        return openstring

    def compile(self, template, stringset):
        stringset = iter(stringset)
        next_string = next(stringset, None)

        po = polib.pofile(template)
        for entry in list(po):
            if next_string is not None:
                is_plural = True if entry.msgid_plural.strip() else False
                if is_plural:
                    compiled = self._compile_plural_entry(entry, next_string)
                else:
                    compiled = self._compile_entry(entry, next_string)
                if compiled:
                    next_string = next(stringset, None)
                    continue
            po.remove(entry)
        return unicode(po)

    def _compile_entry(self, entry, next_string):
        if entry.msgstr == next_string.template_replacement:
            entry.msgstr = next_string.string
            return True
        return False

    def _compile_plural_entry(self, entry, next_string):
        if entry.msgstr_plural.get('0') == next_string.template_replacement:
            entry.msgstr_plural = next_string.string
            return True
        return False
