import itertools
import re
from copy import copy

import polib
import six

from ..exceptions import ParseError
from ..handlers import Handler
from ..strings import OpenString


class PoHandler(Handler):
    """A handler class that parses and compiles `.po` and `.pot` files.

    The `.po` documentation can be found here:
    https://www.gnu.org/software/gettext/manual/html_node/PO-Files.html
    """

    name = "PO"
    extension = "po"

    FUZZY_FLAG = "fuzzy"
    EXTRACTS_RAW = False
    SPECIFIER = re.compile(
        r"%((?:(?P<ord>\d+)\$|\((?P<key>\w+)\))?(?P<fullvar>[+#\- 0]*(?:\d+)?"
        r"(?:\.\d+)?(hh\|h\|l\|ll|j|z|t|L)?(?P<type>[diufFeEgGxXaAoscpn%])))"
    )

    def parse(self, source, is_source=False):
        try:
            po = polib.pofile(source)
        except Exception as e:
            raise ParseError("Error while validating PO file syntax: {}".format(e))
        existing_keys = set()

        # Do this in two passes, on the first pass we collect the data and
        # check that for source files we don't have conflicting PO/POT
        # semantics. In the second pass, we extract the strings and modify the
        # PoFile into a template

        string_data_list = []
        string_types = set()  # choices: EMPTY, SPACES, NOT_EMPTY
        for entry in po:
            msgid = entry.msgid.replace("\\", "\\\\").replace(":", "\\:")
            if not msgid:
                raise ParseError("Found empty msgid.")
            msgid_plural = entry.msgid_plural.replace("\\", "\\\\").replace(":", "\\:")

            pluralized = bool(msgid_plural)
            if pluralized:
                if entry.msgstr.strip():
                    raise ParseError(
                        (
                            "An unexpected msgstr was found on the pluralized entry "
                            "with msgid '{}' and msgid_plural '{}'"
                        ).format(entry.msgid, entry.msgid_plural)
                    )
                key = ":".join((msgid, msgid_plural))
            else:
                if any(entry.msgstr_plural.values()):
                    raise ParseError(
                        (
                            "Found unexpected msgstr[*] on the non pluralized entry "
                            "with msgid '{}'"
                        ).format(entry.msgid)
                    )
                key = msgid

            context = entry.msgctxt if entry.msgctxt is not None else ""
            if (key, context) in existing_keys:
                self._raise_duplicate_error(entry)
            existing_keys.add((key, context))

            string_data = {
                "msgid": entry.msgid,
                "msgid_plural": entry.msgid_plural,
                "key": key,
                "context": context,
                "pluralized": pluralized,
            }
            string_data.update(self._get_metadata(entry))

            if pluralized:
                msgstrs = {
                    int(key): value for key, value in entry.msgstr_plural.items()
                }
            else:
                msgstrs = {5: entry.msgstr}

            if any((string.strip() for string in msgstrs.values())):
                string_type = "NOT_EMPTY"
                if any((not string for string in msgstrs.values())):
                    raise ParseError(
                        (
                            "Incomplete plural forms found on the entry with msgid "
                            "'{}' and msgid_plural '{}'"
                        ).format(entry.msgid, entry.msgid_plural)
                    )
            elif all((not string for string in msgstrs.values())):
                string_type = "EMPTY"
            else:
                string_type = "SPACES"

            if is_source:
                # - If all entries are empty, then this is a POT file and we shouldn't
                #   expect any entries to have a msgstr value.
                # - If all entries are not empty, then this is a PO file and we should
                #   expect all entries to have a msgstr value
                # - msgstr values filled with space characters should be compatible with
                #   both file types, ie
                #   - if the rest of the msgstr values are empty, then msgstrs with
                #     space characters are also considered empty
                #   - if the rest of the msgstr values are not empty, then msgstrs with
                #     space characters are also considered not empty
                if string_type == "EMPTY" and "NOT_EMPTY" in string_types:
                    raise ParseError(
                        (
                            "The entry with msgid '{}' includes an empty msgstr. "
                            "Provide a value and try again"
                        ).format(entry.msgid)
                    )
                elif string_type == "NOT_EMPTY" and "EMPTY" in string_types:
                    raise ParseError(
                        (
                            "A non-empty msgstr was found on the entry with msgid "
                            "'{}'. Remove and try again"
                        ).format(entry.msgid)
                    )
            string_types.add(string_type)

            string_data.update({"msgstrs": msgstrs, "string_type": string_type})
            string_data_list.append(string_data)

        file_type = "PO" if "NOT_EMPTY" in string_types else "POT"
        stringset = []
        order = itertools.count()
        indexes_to_remove = []

        for i, (string_data, entry) in enumerate(zip(string_data_list, po)):
            if is_source:
                if file_type == "POT":
                    # This is a POT file, we must consider the msgids as strings
                    if string_data["pluralized"]:
                        string_values = {
                            0: string_data["msgid"],
                            1: string_data["msgid_plural"],
                        }
                    else:
                        string_values = {5: string_data["msgid"]}
                else:
                    # This is a PO file, we must consider the msgstrs as strings
                    string_values = string_data["msgstrs"]
            else:
                if string_data["string_type"] == "EMPTY":
                    # Translation files are all assumed to be PO files. Empty entries
                    # should be removed from the stringset
                    indexes_to_remove.append(i)
                    continue
                string_values = string_data["msgstrs"]
            openstring = OpenString(
                string_data["key"],
                string_values,
                fuzzy=string_data["fuzzy"],
                order=next(order) if not string_data["fuzzy"] else None,
                context=string_data["context"],
                pluralized=string_data["pluralized"],
                flags=string_data["flags"],
                occurrences=string_data["occurrences"],
                developer_comment=string_data["developer_comment"],
            )
            stringset.append(openstring)
            if string_data["fuzzy"]:
                indexes_to_remove.append(i)
            elif string_data["pluralized"]:
                entry.msgstr_plural = {"0": openstring.template_replacement}
            else:
                entry.msgstr = openstring.template_replacement

        self._smart_remove(po, indexes_to_remove)
        return po, stringset

    def _raise_duplicate_error(self, entry):
        has_context = entry.msgctxt is not None
        pluralized = bool(entry.msgid_plural)
        if has_context:
            if pluralized:
                raise ParseError(
                    (
                        "A duplicate (msgid, msgid_plural) combination was detected "
                        "({}, {}). Use a unique msgid, msgid_plural combination or a "
                        "unique msgctxt to differentiate (the existing msgctxt '{}' is "
                        "a duplicate one)"
                    ).format(entry.msgid, entry.msgid_plural, entry.msgctxt)
                )
            else:
                raise ParseError(
                    (
                        "A duplicate msgid was detected ({}). Use a unique msgid or a "
                        "unique msgctxt to differentiate (the existing msgctxt '{}' is "
                        "a duplicate one)"
                    ).format(entry.msgid, entry.msgctxt)
                )
        else:
            if pluralized:
                raise ParseError(
                    (
                        "A duplicate (msgid, msgid_plural) combination was detected "
                        "({}, {}). Use a unique msgid, msgid_plural combination or add "
                        "a msgctxt to differentiate"
                    ).format(entry.msgid, entry.msgid_plural)
                )
            else:
                raise ParseError(
                    (
                        "A duplicate msgid was detected ({}). Use a unique msgid or "
                        "add a msgctxt to differentiate"
                    ).format(entry.msgid)
                )

    def _get_metadata(self, entry):
        return {
            "occurrences": ", ".join(
                (
                    ":".join((item for item in occurrence))
                    for occurrence in entry.occurrences
                )
            )
            or None,
            "developer_comment": "\n".join((entry.comment, entry.tcomment)),
            "flags": ", ".join(entry.flags),
            "fuzzy": "fuzzy" in entry.flags,
        }

    @staticmethod
    def pofile_to_str(po_file):
        """
        Generate the template for the PO file.

        Use this method instead of six.text_type(po_file)
        in order to avoid the separate handling of obsoleted strings
        by the PO file handler of polib in its __unicode__ method,
        since this affects the order of strings in the tempate and
        as a consequence, strings after obsoleted ones are missing
        in the compiled file.
        """
        result = []
        headers = po_file.header.split("\n")
        for header in headers:
            if header[:1] in [",", ":"]:
                result.append("#%s" % header)
            else:
                result.append("# %s" % header)
        result.append(six.text_type(po_file.metadata_as_entry()))
        for entry in po_file:
            result.append(six.text_type(entry))

        return six.text_type("\n".join(result))

    def compile(self, template, stringset, **kwargs):
        stringset = iter(stringset)
        next_string = next(stringset, None)

        if isinstance(template, polib.POFile):
            po = template
        else:
            po = polib.pofile(template)

        indexes_to_remove = []
        for i, entry in enumerate(po):
            if next_string is not None:
                is_plural = True if entry.msgid_plural.strip() else False
                if is_plural:
                    compiled = self._compile_plural_entry(entry, next_string)
                else:
                    compiled = self._compile_entry(entry, next_string)
                if compiled:
                    next_string = next(stringset, None)
                    continue
            indexes_to_remove.append(i)
        self._smart_remove(po, indexes_to_remove)

        return PoHandler.pofile_to_str(po)

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
        if entry.msgstr_plural.get("0") == next_string.template_replacement:
            entry.msgstr_plural = next_string.string
            return True
        return False

    def _smart_remove(self, po, indexes_to_remove):
        """If you have a big list and go through it and selectively remove entries with
        `.remove()`, it will get slow. This is because each call to `.remove()` will
        search for that item in the list which will get increasingly expensive. Plus,
        the list will have to be continuously shifted after each removal. It is
        preferable to collect the indexes to be removed in a first pass and then use
        `del` using the reversed list of indexes.

        >>> # This is bad
        >>> for item in copy(big_list):
        ...     if some_condition(item):
        ...         big_list.remove(item)

        >>> # This is good
        >>> indexes_to_remove = []
        >>> for i, item in enumerate(big_list):
        ...     if some_condition(item):
        ...         indexes_to_remove.append(i)
        >>> for i in reversed(indexes_to_remove):
        ...     del big_list[i]
        """

        for i in reversed(indexes_to_remove):
            del po[i]
