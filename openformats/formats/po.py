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
        self.only_values = False
        self.only_keys = False
        for entry in self.po:
            openstring = self._handle_entry(entry)
            if openstring is not None:
                stringset.append(openstring)
        return unicode(self.po), stringset

    def _handle_entry(self, entry):
        entry_key, string, pluralized = self._get_string_data(entry)
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

    def _get_string_data(self, entry):
        key, plural_key = self._get_keys(entry)
        if plural_key:
            if entry.msgstr.strip():
                raise ParseError(
                    u"Found msgstr on pluralized entry with msgid `{}` and "
                    u"msgid_plural `{}`".format(key, plural_key)
                )
            pluralized = True
            entry_key = ':'.join([key, plural_key])
        else:
            if entry.msgstr_plural:
                raise ParseError(
                    u"Found msgstr[*] on non pluralized entry with "
                    u"msgid `{}`".format(key)
                )
            pluralized = False
            entry_key = key

        string = self._get_string(entry, pluralized)
        return entry_key, string, pluralized

    def _get_keys(self, entry):
        # Get format keys to avoid colisions
        key = entry.msgid.strip().replace(
            '\\', '\\\\'
        ).replace(':', '\\:')
        plural_key = entry.msgid_plural.strip().replace(
            '\\', '\\\\'
        ).replace(':', '\\:')
        if not key:
            raise ParseError(u"Found empty msgid")
        return key, plural_key

    def _get_string(self, entry, pluralized):
        if pluralized:
            string = entry.msgstr_plural
        else:
            string = entry.msgstr

        is_empty = self._validate_not_empty(entry, string, pluralized)

        if not string or is_empty:
            if not self.only_values:
                self.only_keys = True
                string = entry.msgid if pluralized else {
                    '0': entry.msgid,
                    '1': entry.msgid_plural
                }
            else:
                raise ParseError(u"")
        elif not self.only_keys:
            self.only_values = True
        else:
            raise ParseError(u"")
        return string

    def _validate_not_empty(self, entry, string, pluralized):
        if pluralized:
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
                return True
        elif string.strip() == "":
            return True
        return False

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
