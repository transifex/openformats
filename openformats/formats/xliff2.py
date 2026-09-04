from __future__ import absolute_import

import itertools
import re
from xml.sax import saxutils

from ..exceptions import ParseError
from ..handlers import Handler
from ..strings import OpenString
from ..transcribers import Transcriber
from ..utils.icu import ICUCompiler, ICUParser
from ..utils.xml import NewDumbXml
from ..utils.xmlutils import reraise_syntax_as_parse_errors


class Xliff2Handler(Handler):
    """Parses and compiles XLIFF 2.0 files.

    XLIFF 2.0 (``urn:oasis:names:tc:xliff:document:2.0``) organizes content as
    ``<xliff><file><unit><segment><source>/<target>``. Version 2.0 does not support
    plural, so plurals are expressed as ICU MessageFormat inside
    a single ``<source>``/``<target>``.

    Additional features:
    - developer comments <- ``<unit><notes><note>``
    - character limit <- Size and Length Restriction ``slr:sizeRestriction``
    - occurrences <- Metadata module ``<mda:metaGroup purpose="location">``

    Content is handled in raw mode (``EXTRACTS_RAW = True``): the inner text of
    ``<source>``/``<target>`` is stored and re-emitted verbatim, so entities stay
    encoded and inline elements (``<ph>``, ``<pc>``, ``<mrk>``, ...) are preserved
    as markup rather than being flattened into text.
    """

    name = "XLIFF_V2"
    extension = "xlf"
    EXTRACTS_RAW = True

    SUPPORTED_VERSION = "2.0"

    OTHER_PLURAL_RULE = 5

    # md5 hex hash followed by the OpenString suffix
    PLACEHOLDER_RE = re.compile(r"[0-9a-f]{32}_(?:tr|pl)")

    # A '&' that does not already start a valid entity/character reference
    # (e.g. &amp; &lt; &#160; &#x1F600; &custom;). Used to escape stray
    # ampersands without double-escaping existing entities.
    BARE_AMPERSAND_RE = re.compile(r"&(?!#?[a-zA-Z0-9]+;)")

    # Internal marker set on <target> elements that the parser injected (i.e.
    # were absent from the source). It lets compile() drop such a target when
    # its translation is empty, while keeping targets that existed in the file.
    # It never reaches the compiled output.
    INJECTED_MARKER_ATTR = "tx-injected"

    # Occurrences live in the Metadata module as a metaGroup marked with
    # category="location", holding a sourcefile and a linenumber meta each.
    LOCATION_GROUP_CATEGORY = "location"
    SOURCEFILE_META_TYPE = "sourcefile"
    LINENUMBER_META_TYPE = "linenumber"

    def __init__(self, *args, **kwargs):
        super(Xliff2Handler, self).__init__(*args, **kwargs)
        self._icu_parser = ICUParser(allow_numeric_plural_values=True)
        self.transcriber = None
        self.stringset = None
        self.next_string = None
        self.is_source = False
        self.pseudo = False


    @reraise_syntax_as_parse_errors
    def parse(self, content, is_source=False, **kwargs):
        self.is_source = is_source
        self.transcriber = Transcriber(content)
        source = self.transcriber.source

        root_position = self._root_position(source)
        root = NewDumbXml(source, root_position)
        self._validate_root(root)

        order = itertools.count()
        stringset = []
        seen_keys = set()
        seen_file_ids = set()
        files = list(root.find_children("file"))
        if not files:
            raise ParseError("<xliff> must contain at least one <file> element")
        for file_node in files:
            file_id = file_node.attrib.get("id")
            if not file_id:
                raise ParseError(
                    "<file> element is missing the required 'id' attribute"
                )
            if file_id in seen_file_ids:
                raise ParseError("Duplicate <file> id '{}'".format(file_id))
            seen_file_ids.add(file_id)
            file_notes = self._extract_notes(file_node)
            for unit in file_node.find_descendants("unit"):
                self._parse_unit(
                    unit, file_id, file_notes, stringset, order, seen_keys
                )

        self.transcriber.copy_to_end()
        template = self.transcriber.get_destination()
        return template, stringset

    def _validate_root(self, root):
        if root.tag != "xliff":
            raise ParseError("Root element is not <xliff>")
        version = root.attrib.get("version")
        if version is None:
            raise ParseError("<xliff> element is missing the 'version' attribute")
        if version != self.SUPPORTED_VERSION:
            raise ParseError(
                "Unsupported XLIFF version '{}'; this handler only supports "
                "version {}".format(version, self.SUPPORTED_VERSION)
            )
        if not root.attrib.get("srcLang"):
            raise ParseError("<xliff> element is missing the 'srcLang' attribute")

    def _parse_unit(self, unit, file_id, file_notes, stringset, order, seen_keys):
        if unit.attrib.get("translate") == "no":
            return

        key = unit.attrib.get("id")
        if not key:
            raise ParseError("<unit> element is missing the required 'id' attribute")
        # Fall back to the file-level notes only when the unit has none of its own
        developer_comment = self._extract_notes(unit) or file_notes
        character_limit = self._extract_character_limit(unit)
        occurrences = self._extract_occurrences(unit)

        segments = list(unit.find_children("segment"))
        multiple = len(segments) > 1
        for index, segment in enumerate(segments):
            segment_key = key
            if multiple:
                segment_id = segment.attrib.get("id")
                segment_key = "{}[{}]".format(key, segment_id or index)
            self._register_key(seen_keys, file_id, segment_key)
            self._parse_segment(
                segment,
                segment_key,
                file_id,
                developer_comment,
                character_limit,
                occurrences,
                order,
                stringset,
            )

    def _register_key(self, seen_keys, context, key):
        """Enforce id uniqueness within a <file> (context is the file id)."""
        identifier = (context, key)
        if identifier in seen_keys:
            raise ParseError(
                "Duplicate unit id '{}' found in file '{}'".format(key, context)
            )
        seen_keys.add(identifier)

    def _parse_segment(
        self,
        segment,
        key,
        file_id,
        developer_comment,
        character_limit,
        occurrences,
        order,
        stringset,
    ):
        source_node = next(iter(segment.find_children("source")), None)
        if source_node is None:
            raise ParseError(
                "<segment> in unit '{}' is missing a <source> element".format(key)
            )
        source_content = source_node.content or ""
        if not source_content.strip():
            return

        target_node = next(iter(segment.find_children("target")), None)

        if self.is_source:
            string_content = source_content
        else:
            target_content = target_node.content if target_node is not None else None
            if not (target_content and target_content.strip()):
                return
            string_content = target_content

        icu_string = self._icu_parser.parse(key, string_content)
        if icu_string is not None:
            strings_by_rule = icu_string.strings_by_rule
            if self.OTHER_PLURAL_RULE not in strings_by_rule:
                raise ParseError(
                    "Pluralized unit '{}' is missing the required 'other' "
                    "plural form".format(key)
                )
            openstring = OpenString(
                key,
                {
                    rule: value
                    for rule, value in strings_by_rule.items()
                },
                pluralized=True,
                context=file_id,
                order=next(order),
                developer_comment=developer_comment,
                character_limit=character_limit,
                occurrences=occurrences,
            )
            target_inner = self._plural_target_inner(
                string_content, icu_string, openstring
            )
        else:
            openstring = OpenString(
                key,
                string_content,
                pluralized=False,
                context=file_id,
                order=next(order),
                developer_comment=developer_comment,
                character_limit=character_limit,
                occurrences=occurrences,
            )
            target_inner = openstring.template_replacement

        stringset.append(openstring)

        if target_node is None:
            self._template_inject_target(segment, source_node, target_inner)
        elif self._is_empty_target(target_node):
            # An empty author <target> means "no translation", just like a
            # missing one. Mark it synthetic so compile() treats it the same:
            # dropped when there is no translation and never echoed with the
            # source on a source download.
            self._template_replace_empty_target(target_node, target_inner)
        else:
            self._template_replace_target(target_node, target_inner)

    @staticmethod
    def _is_empty_target(target_node):
        content = target_node.content
        return not (content and content.strip())

    def _plural_target_inner(self, source_content, icu_string, openstring):
        """Build the target inner text for a plural string, preserving the ICU
        wrapper (e.g. ``{count, plural, <hash>_pl}``) so the compile phase can
        expand the placeholder into the target language's plural forms."""
        start = icu_string.current_position
        end = start + len(icu_string.string_to_replace)
        prefix = source_content[:start]
        suffix = source_content[end:]
        return prefix + openstring.template_replacement + suffix

    def _template_replace_target(self, target_node, target_inner):
        # Only non-empty targets reach here (empty and self-closing ones route
        # to _template_replace_empty_target), so text_position is always set.
        self.transcriber.copy_until(target_node.text_position)
        self.transcriber.add(target_inner)
        self.transcriber.skip_until(target_node.content_end)

    def _template_replace_empty_target(self, target_node, target_inner):
        # Replace an empty author <target> (``<target></target>`` or
        # ``<target/>``) with a marked placeholder, so it is handled like an
        # injected target. Any attributes on the empty element are dropped.
        self.transcriber.copy_until(target_node.position)
        self.transcriber.add(
            '<target {}="1">{}</target>'.format(
                self.INJECTED_MARKER_ATTR, target_inner
            )
        )
        self.transcriber.skip_until(target_node.tail_position)

    def _template_inject_target(self, segment, source_node, target_inner):
        # No <target> exists (source-only file): inject one right after <source>,
        # tagged so compile() can tell it apart from author-provided targets.
        self.transcriber.copy_until(source_node.tail_position)
        separator = segment.text if (segment.text and not segment.text.strip()) else ""
        self.transcriber.add(
            '{}<target {}="1">{}</target>'.format(
                separator, self.INJECTED_MARKER_ATTR, target_inner
            )
        )

    def _extract_notes(self, element):
        notes = next(iter(element.find_children("notes")), None)
        if notes is None:
            return ""
        parts = []
        for note in notes.find_children("note"):
            text = (note.content or "").strip()
            if not text:
                continue
            parts.append(saxutils.unescape(text))
        return "\n".join(parts)

    def _extract_character_limit(self, unit):
        value = unit.attrib.get("slr:sizeRestriction")
        if value is None:
            return None
        try:
            limit = int(value)
        except (TypeError, ValueError):
            return None
        return limit if limit > 0 else None

    def _extract_occurrences(self, unit):
        metadata = next(iter(unit.find_children("mda:metadata")), None)
        if metadata is None:
            return None
        locations = []
        for group in metadata.find_descendants("mda:metaGroup"):
            if group.attrib.get("category") != self.LOCATION_GROUP_CATEGORY:
                continue
            sourcefile = linenumber = None
            for meta in group.find_children("mda:meta"):
                meta_type = meta.attrib.get("type")
                if meta_type == self.SOURCEFILE_META_TYPE:
                    sourcefile = (meta.content or "").strip()
                elif meta_type == self.LINENUMBER_META_TYPE:
                    linenumber = (meta.content or "").strip()
            if not sourcefile:
                continue
            if linenumber:
                locations.append("{}:{}".format(sourcefile, linenumber))
            else:
                locations.append(sourcefile)
        return ", ".join(locations) if locations else None

    def compile(self, template, stringset, is_source=False, language_info=None, **kwargs):
        root_position = self._root_position(template)
        prefix = template[:root_position]
        body = template[root_position:]

        if not is_source and language_info and language_info.get("code"):
            body = self._set_target_language(body, language_info["code"])

        self.transcriber = Transcriber(body)
        source = self.transcriber.source
        root = NewDumbXml(source)

        self.stringset = iter(stringset)
        self.next_string = self._get_next_string()
        self.is_source = is_source
        self.pseudo = bool(kwargs.get("pseudo"))

        for unit in root.find_descendants("unit"):
            self._compile_unit(unit)

        self.transcriber.copy_to_end()
        return prefix + self.transcriber.get_destination()

    def _compile_unit(self, unit):
        """Apply the compile plan to a <unit>.

        A <segment> whose string was dropped by the compile mode (e.g. the
        translated entries under UNTRANSLATED mode) is removed outright. The
        enclosing <unit> is removed only when that leaves it with no <segment>
        children; otherwise just the dropped segment(s) go.
        """
        plans = []
        removed = 0
        for segment in unit.find_children("segment"):
            plan = self._plan_segment(segment)
            plans.append((segment,) + plan)
            if plan[0] == "remove":
                removed += 1

        if plans and removed == len(plans):
            self._remove_element(unit)
            return

        for segment, action, target, new_inner, injected in plans:
            if action == "remove":
                self._remove_element(segment)
            elif action == "write":
                self._write_target(target, new_inner, injected)
            elif action == "strip":
                self._remove_element(target)

    def _plan_segment(self, segment):
        """Decide what to do with a <segment>, advancing the stringset cursor.

        Returns ``(action, target, new_inner, injected)`` where action is one of:
        ``write`` (emit the translation), ``strip`` (drop just the <target>,
        keeping a source-only segment), ``remove`` (drop the whole segment), or
        ``untouched`` (leave it verbatim, e.g. a translate="no" unit).
        """
        target = next(iter(segment.find_children("target")), None)
        if target is None:
            return ("untouched", None, None, False)
        inner = target.content
        if inner is None:
            return ("untouched", target, None, False)
        match = self.PLACEHOLDER_RE.search(inner)
        if match is None:
            # A target without a placeholder (e.g. a translate="no" unit or a
            # pre-existing translation) is left untouched.
            return ("untouched", target, None, False)

        injected = target.attrib.get(self.INJECTED_MARKER_ATTR) == "1"
        token = match.group(0)
        if self.next_string is not None and \
                token == self.next_string.template_replacement:
            if self.next_string.pluralized:
                rendered = ICUCompiler().serialize_strings(
                    {
                        rule: self.escape(value)
                        for rule, value in self.next_string.string.items()
                    },
                    delimiter=" ",
                )
                new_inner = inner.replace(token, rendered)
                # The ICU wrapper keeps new_inner non-empty even when every
                # plural form is blank, so judge emptiness on the form values.
                has_content = any(
                    value and value.strip()
                    for value in self.next_string.string.values()
                )
            else:
                new_inner = self.escape(self.next_string.string)
                has_content = bool(new_inner)
            self.next_string = self._get_next_string()
            if self.is_source and injected and not self.pseudo:
                # Real source download: a synthetic target (the source had no
                # <target>, or an empty one) must not echo the source; keep the
                # segment source-only. Pseudo downloads are exempt.
                return ("strip", target, None, injected)
            if has_content:
                return ("write", target, new_inner, injected)
            # Present but empty (e.g. UNTRANSLATED missing_strategy=empty, or an
            # all-blank plural): keep the segment, dropping just the <target>.
            return ("strip", target, None, injected)

        # No matching translation (dropped by the compile mode): remove the whole
        # segment; the unit goes too if it has no segments left.
        return ("remove", target, None, injected)

    def _write_target(self, target, new_inner, injected):
        if injected:
            # Rewrite a clean <target>, dropping the internal marker attribute.
            self.transcriber.copy_until(target.position)
            self.transcriber.add("<target>")
            self.transcriber.add(new_inner)
            self.transcriber.skip_until(target.content_end)
        else:
            self.transcriber.copy_until(target.text_position)
            self.transcriber.add(new_inner)
            self.transcriber.skip_until(target.content_end)

    def _remove_element(self, element):
        """Remove the whole element (<target>, <segment> or <unit>), along with
        the indentation whitespace that precedes it, so no blank line is left
        behind."""
        source = self.transcriber.source
        start = element.position
        while start > 0 and source[start - 1].isspace():
            start -= 1
        self.transcriber.copy_until(start)
        self.transcriber.skip_until(element.tail_position)

    def _set_target_language(self, body, code):
        def add_attr(match):
            tag = match.group(0)
            if "trgLang=" in tag:
                return re.sub(r'trgLang="[^"]*"', 'trgLang="{}"'.format(code), tag)
            return tag[:-1] + ' trgLang="{}"'.format(code) + tag[-1]

        return re.sub(r"<xliff\b[^>]*>", add_attr, body, count=1)

    def _get_next_string(self):
        try:
            return next(self.stringset)
        except StopIteration:
            return None

    def _root_position(self, content):
        try:
            return content.index("<xliff")
        except ValueError:
            raise ParseError("Root element <xliff> not found")

    @staticmethod
    def escape(string):
        # Raw mode (EXTRACTS_RAW = True): <source>/<target> content is emitted
        # verbatim, keeping valid entities and inline elements (<ph>, <pc>,
        # <mrk>, ...) intact as markup. We only guard against a *bare* ``&``
        # (one that does not already start a valid character/entity reference),
        # which would otherwise make the compiled XML non-well-formed. Escaping
        # ``<`` here is deliberately avoided: it is ambiguous with inline tags.
        return Xliff2Handler.BARE_AMPERSAND_RE.sub("&amp;", string)

    @staticmethod
    def unescape(string):
        # Required by the raw-mode handler contract (see CommonFormatTestMixin).
        # Raw mode keeps <source>/<target> content encoded, so there is nothing
        # to decode here: returning it unchanged preserves entities and inline
        # markup. (Developer notes, which are display-only, are decoded
        # separately in _extract_notes.)
        return string
