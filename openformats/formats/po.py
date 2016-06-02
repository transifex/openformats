import copy
import itertools

import polib

from ..handlers import Handler
from ..strings import OpenString
from ..exceptions import ParseError


class PoHandler(Handler):
    """A handler class that parses and compiles `.po` and `.pot` files.

    The `.po` documentation can be found here:
    https://www.gnu.org/software/gettext/manual/html_node/PO-Files.html
    """

    name = "PO"
    extension = "po"

    FUZZY_FLAG = 'fuzzy'
    EXTRACTS_RAW = False
    SPECIFIER = (
        '%((?:(?P<ord>\d+)\$|\((?P<key>\w+)\))?(?P<fullvar>[+#\- 0]*(?:\d+)?'
        '(?:\.\d+)?(hh\|h\|l\|ll|j|z|t|L)?(?P<type>[diufFeEgGxXaAoscpn%])))'
    )

    def parse(self, content, is_source=False):
        stringset = []
        self.is_source = is_source
        self.order_generator = itertools.count()
        po = polib.pofile(content)
        self.only_values = False
        self.only_keys = False
        self.new_po = copy.copy(po)
        self.unique_keys = set()
        for entry in po:
            openstring = self._handle_entry(entry)
            if openstring is not None:
                stringset.append(openstring)
        return unicode(self.new_po), stringset

    def _handle_entry(self, entry):
        """Handles a po file entry.
        Will retrieve entry's information (pluralized, fuzzy) and create
        an openstring with all relevant information.

        :param entry: The po's file entry to handle.
        :returns: An openstring if one was creates or None is the entry's
                    string was None.

        NOTE: In case of fuzzy entry or openstring == None it will remove
        the entry from the compiled po.
        """
        entry_key, string, pluralized = self._get_string_data(entry)
        if string is not None:
            openstring_kwargs = {'pluralized': pluralized}
            # Check fuzziness
            if self.FUZZY_FLAG in entry.flags:
                # If fuzzy create flag and remove from template
                openstring_kwargs['fuzzy'] = True
                self.new_po.remove(entry)
            else:
                openstring_kwargs['order'] = next(self.order_generator)
            return self._create_openstring(
                entry, entry_key, string, openstring_kwargs
            )
        self.new_po.remove(entry)
        return None

    def _get_string_data(self, entry):
        """Retrieves the string and it's information from the entry.

        :param entry: The po's file entry containing the string.
        :returns: A 3-tuple withe the key indentifying the entry, the entry's
                    string and True if the string is pluralized else False.
        :raises: ParseError if a non pluralized entry contains pluralized
                    string or if a pluralized entry contains a non pluralized
                    string.
        """
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
        self._validate_unique_key(entry_key, pluralized, entry)
        string = self._get_string(entry, pluralized)
        return entry_key, string, pluralized

    def _get_keys(self, entry):
        """Retrieves the keys indentifying the entry.
        Before returning the keys it escapes them to avoid hash colisions.

        :param entry: The entry to retrieve the keys from.
        :returns: A 2-tuple containing the key and the plural key.
                    For non pluralized entries the plural key is an empty
                    string.
        """
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

    def _validate_unique_key(self, key, pluralized, entry):
        if key in self.unique_keys:
            if not pluralized:
                msg = u"Found duplicate msgid (`{}`).".format(entry.msgid)
            else:
                msg = (
                    u"Found duplicate msgid and msgid_plural "
                    u"(`{}`, `{}`).".format(
                        entry.msgid, entry.msgid_plural
                    )
                )
            raise ParseError(msg)
        self.unique_keys.add(key)

    def _get_string(self, entry, pluralized):
        """Returns the string of the entry.
        It starts by retrieving the msgstr attribute from the entry. If the
        msgstr is empty it will fallback to the msgid.

        :param entry: The entry to retrieve the string from.
        :param pluralized: If True expect a pluralized string.
        :returns: The string of the entry.
        :raises: ParseError if incosistency is found on the file. To be more
                    verbose: Either all msgstr attributes are fille or none is.
        """
        if pluralized:
            string = entry.msgstr_plural
        else:
            string = entry.msgstr

        is_empty = self._validate_empty(entry, string, pluralized)

        if is_empty and not self.is_source:
            return None
        elif is_empty:
            if not self.only_values:
                self.only_keys = True
                string = entry.msgid if pluralized else {
                    '0': entry.msgid,
                    '1': entry.msgid_plural
                }
            else:
                raise ParseError(
                    u"Either all `msgstr`s must be filled or none."
                )
        elif not self.only_keys:
            self.only_values = True
        else:
            raise ParseError(
                u"Either all `msgstr`s must be filled or none."
            )
        return string

    def _validate_empty(self, entry, string, pluralized):
        """Checks if a string is empty or not.
        :param entry: The entry that contained the string.
        :param string: The string to validate.
        :param pluralized: If true the string is pluralized.

        :returns: True is the string is empty else False.
        :raises: ParseError if the string is pluralized and not all the plurals
                    are filles (at least one is).
        """
        if not string:
            return True
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
        """Cretes and openstring.
        Will also place a hash at the msgstr attribute of the entry for the
        template.

        :param entry: The entry the openstring is created from.
        :param entry_key: The key indentifying the entry.
        :param string: The string the entry contains.
        :param openstring_kwargs: Extra information about the string.
        :returns: The openstring.
        """
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
        """Compiles the current non pluralized entry.
        If the current entry's matches the openstring compiles the string if
        it does.

        :param entry: The entry to check.
        :param next_string: The openstring to compile.
        """
        if entry.msgstr == next_string.template_replacement:
            entry.msgstr = next_string.string
            return True
        return False

    def _compile_plural_entry(self, entry, next_string):
        """Compiles the current pluralized entry.
        If the current entry's matches the openstring compiles the string if
        it does.

        :param entry: The entry to check.
        :param next_string: The openstring to compile.
        """
        if entry.msgstr_plural.get('0') == next_string.template_replacement:
            entry.msgstr_plural = next_string.string
            return True
        return False
