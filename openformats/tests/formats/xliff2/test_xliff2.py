# -*- coding: utf-8 -*-
import unittest
from xml.etree import ElementTree as ET

import six

from openformats.exceptions import ParseError
from openformats.formats.xliff2 import Xliff2Handler
from openformats.tests.formats.common import CommonFormatTestMixin


class Xliff2TestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = Xliff2Handler
    TESTFILE_BASE = "openformats/tests/formats/xliff2/files"

    def setUp(self):
        super(Xliff2TestCase, self).setUp()
        self.handler = Xliff2Handler()

    def _parse(self, content):
        return self.handler.parse(content, is_source=True)

    # -- metadata parity ---------------------------------------------------

    def test_developer_comment_from_notes(self):
        _, stringset = self._parse(self.data["1_en"])
        greeting = stringset[0]
        self.assertEqual(
            greeting.developer_comment, "Shown on the login screen"
        )

    def test_file_level_notes_are_fallback(self):
        content = _wrap(
            u'<notes>'
            u'<note category="general">General file guidance.</note>'
            u'</notes>'
            u'<unit id="own">'
            u'<notes><note>Unit specific note.</note></notes>'
            u'<segment><source>Has its own</source></segment>'
            u'</unit>'
            u'<unit id="inherits">'
            u'<segment><source>Uses file note</source></segment>'
            u'</unit>'
        )
        _, stringset = self.handler.parse(content, is_source=True)
        by_key = {s.key: s for s in stringset}
        # Unit with its own note keeps it; category is ignored.
        self.assertEqual(by_key["own"].developer_comment, "Unit specific note.")
        # Unit without notes inherits the file-level note.
        self.assertEqual(
            by_key["inherits"].developer_comment, "General file guidance."
        )

    def test_character_limit_from_size_restriction(self):
        _, stringset = self._parse(self.data["1_en"])
        self.assertEqual(stringset[0].character_limit, 30)
        self.assertIsNone(stringset[1].character_limit)

    def test_occurrences_from_metadata_location(self):
        _, stringset = self._parse(self.data["1_en"])
        self.assertEqual(stringset[0].occurrences, "login.py:42")
        self.assertIsNone(stringset[1].occurrences)

    def test_occurrences_multiple_groups_and_ignored_groups(self):
        content = _wrap(
            u'<unit id="u1">'
            u'<mda:metadata>'
            u'<mda:metaGroup category="location">'
            u'<mda:meta type="sourcefile">a/b.py</mda:meta>'
            u'<mda:meta type="linenumber">10</mda:meta>'
            u'</mda:metaGroup>'
            u'<mda:metaGroup category="location">'
            u'<mda:meta type="sourcefile">c/d.py</mda:meta>'
            u'<mda:meta type="linenumber">20</mda:meta>'
            u'</mda:metaGroup>'
            u'<mda:metaGroup category="other">'
            u'<mda:meta type="sourcefile">ignored.py</mda:meta>'
            u'<mda:meta type="linenumber">99</mda:meta>'
            u'</mda:metaGroup>'
            u'</mda:metadata>'
            u'<segment><source>Hello</source></segment>'
            u'</unit>'
        )
        _, stringset = self.handler.parse(content, is_source=True)
        self.assertEqual(stringset[0].occurrences, "a/b.py:10, c/d.py:20")

    def test_context_is_file_id(self):
        _, stringset = self._parse(self.data["1_en"])
        self.assertTrue(all(s.context == "f1" for s in stringset))

    # -- plurals -----------------------------------------------------------

    def test_icu_plural_extraction(self):
        _, stringset = self._parse(self.data["1_en"])
        plural = stringset[-1]
        self.assertTrue(plural.pluralized)
        self.assertEqual(
            plural.string,
            {
                1: "You have # unread notification",
                5: "You have # unread notifications",
            },
        )

    def test_invalid_icu_plural_rule_raises(self):
        content = _wrap(
            u'<unit id="u1"><segment>'
            u'<source>{n, plural, bogus {a} other {b}}</source>'
            u'</segment></unit>'
        )
        with self.assertRaises(ParseError):
            self.handler.parse(content, is_source=True)

    # -- structure ---------------------------------------------------------

    def test_translate_no_is_skipped(self):
        content = _wrap(
            u'<unit id="keep"><segment><source>Keep me</source></segment></unit>'
            u'<unit id="skip" translate="no">'
            u'<segment><source>Ignore me</source></segment></unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        self.assertEqual([s.key for s in stringset], ["keep"])
        # The skipped unit is left verbatim (no placeholder injected)
        self.assertIn("<source>Ignore me</source>", template)
        self.assertNotIn("Ignore me</target>", template)

    def test_multiple_segments_get_unique_keys(self):
        content = _wrap(
            u'<unit id="multi">'
            u'<segment id="s1"><source>First</source></segment>'
            u'<segment id="s2"><source>Second</source></segment>'
            u'</unit>'
        )
        _, stringset = self.handler.parse(content, is_source=True)
        self.assertEqual([s.key for s in stringset], ["multi[s1]", "multi[s2]"])

    def test_target_injected_for_source_only_unit(self):
        content = _wrap(
            u'<unit id="only"><segment><source>Hello</source></segment></unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        self.assertIn("<target", template)
        translated = _translate(stringset, "Bonjour")
        compiled = self.handler.compile(template, translated)
        self.assertIn("<source>Hello</source>", compiled)
        self.assertIn("<target>Bonjour</target>", compiled)
        # The internal injection marker never leaks into the output.
        self.assertNotIn(self.handler.INJECTED_MARKER_ATTR, compiled)

    def test_empty_translation_removes_author_target_on_translation_download(self):
        # On a translation download, an untranslated unit drops its <target>,
        # even if the source file provided one.
        content = _wrap(
            u'<unit id="u1">'
            u'<segment><source>Hello</source><target>Hello</target></segment>'
            u'</unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        _set_string(stringset[0], "")
        compiled = self.handler.compile(template, stringset)
        self.assertIn("<source>Hello</source>", compiled)
        self.assertNotIn("<target", compiled)

    def test_empty_source_target_removed_on_source_download(self):
        # A pre-existing empty author <target> is treated as "no translation":
        # on a source download it is removed rather than echoing the source.
        content = _wrap(
            u'<unit id="filled">'
            u'<segment><source>Hi</source><target>Hi</target></segment>'
            u'</unit>'
            u'<unit id="blank">'
            u'<segment><source>Bye</source><target></target></segment>'
            u'</unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        # SOURCE_MODE resolves every string to its source.
        by_key = {s.key: s for s in stringset}
        _set_string(by_key["filled"], "Hi")
        _set_string(by_key["blank"], "Bye")
        compiled = self.handler.compile(template, stringset, is_source=True)
        self.assertIn("<target>Hi</target>", compiled)
        self.assertIn("<source>Bye</source>", compiled)
        # The empty target is dropped, not filled with the source.
        self.assertNotIn("<target>Bye</target>", compiled)
        self.assertNotIn("<target></target>", compiled)

    def test_empty_translation_removes_injected_target(self):
        # A <target> the parser injected (source-only unit) is dropped when the
        # translation is empty, so the file stays source-only.
        content = _wrap(
            u'<unit id="u1"><segment><source>Hello</source></segment></unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        _set_string(stringset[0], "")
        compiled = self.handler.compile(template, stringset)
        self.assertIn("<source>Hello</source>", compiled)
        self.assertNotIn("<target", compiled)

    def test_source_download_omits_injected_targets(self):
        # Source-language download (is_source=True) fills every string with the
        # source. Units that had a <target> keep it; source-only units must not
        # get one echoed back.
        content = _wrap(
            u'<unit id="author">'
            u'<segment><source>Hi</source><target>Hi</target></segment>'
            u'</unit>'
            u'<unit id="only"><segment><source>Bye</source></segment></unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        # SOURCE_MODE resolves every string to its source.
        by_key = {s.key: s for s in stringset}
        _set_string(by_key["author"], "Hi")
        _set_string(by_key["only"], "Bye")
        compiled = self.handler.compile(template, stringset, is_source=True)
        self.assertIn("<target>Hi</target>", compiled)
        self.assertIn("<source>Bye</source>", compiled)
        self.assertNotIn("<target>Bye</target>", compiled)

    def test_pseudo_download_writes_injected_targets(self):
        # A pseudo download runs on the source language (is_source=True) but must
        # emit a <target> with the pseudo text even for source-only units.
        content = _wrap(
            u'<unit id="only"><segment><source>Hello</source></segment></unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        _set_string(stringset[0], "[Ĥéļļö]")
        compiled = self.handler.compile(
            template, stringset, is_source=True, pseudo=True
        )
        self.assertIn("<source>Hello</source>", compiled)
        self.assertIn("<target>[Ĥéļļö]</target>", compiled)
        self.assertNotIn(self.handler.INJECTED_MARKER_ATTR, compiled)

    # -- compile-mode removal ("remove" strategy) --------------------------

    def test_removed_string_drops_segment_keeps_unit(self):
        # A dropped string removes only its <segment> when the <unit> has other
        # segments left.
        content = _wrap(
            u'<unit id="u1">'
            u'<segment id="s1"><source>First</source></segment>'
            u'<segment id="s2"><source>Second</source></segment>'
            u'</unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        # Emulate a compile mode that drops the first segment's string.
        kept = [s for s in stringset if s.key.endswith("[s2]")]
        _set_string(kept[0], "Deux")
        compiled = self.handler.compile(template, kept)
        self.assertNotIn("First", compiled)
        self.assertIn("<source>Second</source>", compiled)
        self.assertIn("<target>Deux</target>", compiled)
        # The unit survives because a segment remains.
        self.assertIn('<unit id="u1">', compiled)
        ET.fromstring(compiled)

    def test_removed_string_drops_whole_unit_when_empty(self):
        # A dropped string removes the whole <unit> when no segment is left.
        content = _wrap(
            u'<unit id="keep"><segment><source>Keep me</source></segment></unit>'
            u'<unit id="drop"><segment><source>Drop me</source></segment></unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        kept = [s for s in stringset if s.key == "keep"]
        _set_string(kept[0], "Gardez")
        compiled = self.handler.compile(template, kept)
        self.assertIn('<unit id="keep">', compiled)
        self.assertIn("<target>Gardez</target>", compiled)
        # The dropped unit is gone entirely — no leftover source-only unit.
        self.assertNotIn('<unit id="drop">', compiled)
        self.assertNotIn("Drop me", compiled)
        ET.fromstring(compiled)

    def test_untranslated_mode_drops_translated_keeps_untranslated(self):
        # Mirrors UNTRANSLATED: translated entries are absent from the stringset
        # (removed), untranslated ones are present but empty. Translated units
        # are dropped entirely; untranslated ones stay as source-only.
        content = _wrap(
            u'<unit id="translated">'
            u'<segment><source>Hello</source></segment></unit>'
            u'<unit id="untranslated">'
            u'<segment><source>World</source></segment></unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        by_key = {s.key: s for s in stringset}
        _set_string(by_key["untranslated"], "")
        compiled = self.handler.compile(template, [by_key["untranslated"]])
        # Translated unit removed entirely.
        self.assertNotIn('<unit id="translated">', compiled)
        self.assertNotIn("Hello", compiled)
        # Untranslated unit kept, source-only (no <target>).
        self.assertIn('<unit id="untranslated">', compiled)
        self.assertIn("<source>World</source>", compiled)
        self.assertNotIn("<target", compiled)
        ET.fromstring(compiled)

    def test_empty_plural_translation_drops_target(self):
        # An all-blank plural translation must drop the <target>, not emit an
        # empty ICU wrapper (e.g. {n, plural, one {} other {}}).
        content = _wrap(
            u'<unit id="p1"><segment>'
            u'<source>{n, plural, one {# thing} other {# things}}</source>'
            u'</segment></unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        _set_string(stringset[0], "")
        compiled = self.handler.compile(template, stringset)
        self.assertIn(
            "<source>{n, plural, one {# thing} other {# things}}</source>",
            compiled,
        )
        self.assertNotIn("<target", compiled)
        self.assertNotIn("plural, one {} other {}", compiled)
        ET.fromstring(compiled)

    # -- translation upload (is_source=False) ------------------------------

    def test_translation_upload_extracts_target(self):
        # On a translation upload the extracted string is the <target> value,
        # not the <source>.
        content = _wrap(
            u'<unit id="u1">'
            u'<segment><source>Hello</source><target>Bonjour</target></segment>'
            u'</unit>'
        )
        _, stringset = self.handler.parse(content, is_source=False)
        self.assertEqual([s.string for s in stringset], ["Bonjour"])

    def test_translation_upload_skips_units_without_target(self):
        # Units with no <target> (or an empty one) carry no translation and are
        # dropped from the stringset, mirroring the XLIFF 1.2 handler.
        content = _wrap(
            u'<unit id="translated">'
            u'<segment><source>Hello</source><target>Bonjour</target></segment>'
            u'</unit>'
            u'<unit id="missing">'
            u'<segment><source>World</source></segment>'
            u'</unit>'
            u'<unit id="empty">'
            u'<segment><source>Again</source><target></target></segment>'
            u'</unit>'
        )
        _, stringset = self.handler.parse(content, is_source=False)
        self.assertEqual([s.key for s in stringset], ["translated"])

    def test_translation_upload_extracts_plural_target(self):
        content = _wrap(
            u'<unit id="items"><segment>'
            u'<source>{count, plural, one {# thing} other {# things}}</source>'
            u'<target>{count, plural, one {# chose} other {# choses}}</target>'
            u'</segment></unit>'
        )
        _, stringset = self.handler.parse(content, is_source=False)
        plural = stringset[0]
        self.assertTrue(plural.pluralized)
        self.assertEqual(plural.string, {1: "# chose", 5: "# choses"})

    # -- raw content (entities + inline markup) ----------------------------

    def test_entities_kept_encoded_on_parse(self):
        # Raw mode: entities in <source>/<target> stay encoded when stored, so
        # the string remains a well-formed XML fragment.
        content = _wrap(
            u'<unit id="u1"><segment>'
            u'<source>Price &amp; tax &lt; 5 &gt; 1</source>'
            u'</segment></unit>'
        )
        _, stringset = self.handler.parse(content, is_source=True)
        self.assertEqual(stringset[0].string, "Price &amp; tax &lt; 5 &gt; 1")

    def test_inline_elements_preserved_round_trip(self):
        # Inline elements (<ph>, <pc>, <mrk>, ...) must survive parse+compile
        # verbatim rather than being escaped into literal text.
        content = _wrap(
            u'<unit id="u1"><segment>'
            u'<source>Hello <ph id="1" equiv="X"/> '
            u'<pc id="2">world</pc> &amp; more</source>'
            u'<target>Hello <ph id="1" equiv="X"/> '
            u'<pc id="2">world</pc> &amp; more</target>'
            u'</segment></unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        self.assertEqual(
            stringset[0].string,
            u'Hello <ph id="1" equiv="X"/> <pc id="2">world</pc> &amp; more',
        )
        compiled = self.handler.compile(template, stringset, is_source=True)
        self.assertIn(
            u'<target>Hello <ph id="1" equiv="X"/> '
            u'<pc id="2">world</pc> &amp; more</target>',
            compiled,
        )
        # Inline tags are not escaped into text.
        self.assertNotIn("&lt;ph", compiled)
        ET.fromstring(compiled)

    def test_bare_ampersand_is_escaped_on_compile(self):
        # A translation containing an unescaped '&' must be escaped so the
        # compiled XLIFF stays well-formed, without double-escaping existing
        # entities or touching inline markup.
        content = _wrap(
            u'<unit id="u1"><segment>'
            u'<source>Plain</source><target>Plain</target>'
            u'</segment></unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        _set_string(stringset[0], u'Tom & Jerry &amp; <ph id="1"/>')
        compiled = self.handler.compile(template, stringset)
        self.assertIn(
            u'<target>Tom &amp; Jerry &amp; <ph id="1"/></target>', compiled
        )
        ET.fromstring(compiled)

    def test_raw_round_trip_reproduces_source(self):
        # A source-language compile of an unchanged file reproduces it exactly.
        content = _wrap(
            u'<unit id="u1"><segment>'
            u'<source>A &amp; B</source><target>A &amp; B</target>'
            u'</segment></unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        self.assertEqual(stringset[0].string, "A &amp; B")
        compiled = self.handler.compile(template, stringset, is_source=True)
        self.assertEqual(compiled, content)

    def test_plural_raw_round_trip(self):
        content = _wrap(
            u'<unit id="u1"><segment>'
            u'<source>{n, plural, one {A &amp; b} other {A &amp; bs}}</source>'
            u'<target>{n, plural, one {A &amp; b} other {A &amp; bs}}</target>'
            u'</segment></unit>'
        )
        _, stringset = self.handler.parse(content, is_source=True)
        self.assertEqual(stringset[0].string, {1: "A &amp; b", 5: "A &amp; bs"})
        template, stringset = self.handler.parse(content, is_source=True)
        compiled = self.handler.compile(template, stringset, is_source=True)
        self.assertIn("one {A &amp; b} other {A &amp; bs}", compiled)
        ET.fromstring(compiled)

    def test_set_target_language_on_root_only(self):
        template, stringset = self.handler.parse(self.data["1_en"])
        compiled = self.handler.compile(
            template, stringset, language_info={"name": "Greek", "code": "el"}
        )
        self.assertIn('srcLang="en" trgLang="el"', compiled)
        self.assertNotIn("<file id=\"f1\" trgLang", compiled)

    # -- parse errors ------------------------------------------------------

    def test_missing_root_raises(self):
        with self.assertRaises(ParseError) as ctx:
            self.handler.parse(u"<not-xliff></not-xliff>")
        self.assertEqual(
            six.text_type(ctx.exception), "Root element <xliff> not found"
        )

    def test_unsupported_version_raises(self):
        content = (
            u'<xliff version="1.2" srcLang="en" '
            u'xmlns="urn:oasis:names:tc:xliff:document:1.2"></xliff>'
        )
        with self.assertRaises(ParseError) as ctx:
            self.handler.parse(content)
        self.assertIn("Unsupported XLIFF version '1.2'", six.text_type(ctx.exception))

    def test_missing_srclang_raises(self):
        content = (
            u'<xliff version="2.0" '
            u'xmlns="urn:oasis:names:tc:xliff:document:2.0"></xliff>'
        )
        with self.assertRaises(ParseError) as ctx:
            self.handler.parse(content)
        self.assertEqual(
            six.text_type(ctx.exception),
            "<xliff> element is missing the 'srcLang' attribute",
        )

    # -- structural validation ---------------------------------------------

    def test_no_file_raises(self):
        content = (
            u'<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" '
            u'version="2.0" srcLang="en"></xliff>'
        )
        with self.assertRaises(ParseError) as ctx:
            self.handler.parse(content, is_source=True)
        self.assertIn("at least one <file>", six.text_type(ctx.exception))

    def test_missing_file_id_raises(self):
        content = (
            u'<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" '
            u'version="2.0" srcLang="en"><file>'
            u'<unit id="u1"><segment><source>Hi</source></segment></unit>'
            u'</file></xliff>'
        )
        with self.assertRaises(ParseError) as ctx:
            self.handler.parse(content, is_source=True)
        self.assertIn("<file> element is missing", six.text_type(ctx.exception))

    def test_duplicate_file_id_raises(self):
        content = (
            u'<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" '
            u'version="2.0" srcLang="en">'
            u'<file id="f1">'
            u'<unit id="u1"><segment><source>Hi</source></segment></unit>'
            u'</file>'
            u'<file id="f1">'
            u'<unit id="u2"><segment><source>Bye</source></segment></unit>'
            u'</file></xliff>'
        )
        with self.assertRaises(ParseError) as ctx:
            self.handler.parse(content, is_source=True)
        self.assertIn("Duplicate <file> id", six.text_type(ctx.exception))

    def test_missing_unit_id_raises(self):
        content = _wrap(
            u'<unit><segment><source>Hi</source></segment></unit>'
        )
        with self.assertRaises(ParseError) as ctx:
            self.handler.parse(content, is_source=True)
        self.assertIn("<unit> element is missing", six.text_type(ctx.exception))

    def test_duplicate_unit_id_keeps_the_first(self):
        """A repeated unit id is ignored, keeping the first occurrence.

        Mirrors the XLIFF 1.2 handler, which skips a <trans-unit> whose id it
        has already seen in the current <file> instead of failing the upload.
        """
        content = (
            u'<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" '
            u'xmlns:slr="urn:oasis:names:tc:xliff:sizerestriction:2.0" '
            u'version="2.0" srcLang="en">'
            u'<file id="f1">'
            u'<unit id="dup" slr:sizeRestriction="10">'
            u'<notes><note>First note</note></notes>'
            u'<segment><source>Hi</source></segment>'
            u'</unit>'
            u'<unit id="dup" slr:sizeRestriction="99">'
            u'<notes><note>Second note</note></notes>'
            u'<segment><source>Bye</source></segment>'
            u'</unit>'
            u'<unit id="after"><segment><source>Tail</source></segment></unit>'
            u'</file></xliff>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        self.assertEqual([s.key for s in stringset], ["dup", "after"])
        # The first occurrence wins outright: source, notes and metadata.
        self.assertEqual(stringset[0].string, "Hi")
        self.assertEqual(stringset[0].developer_comment, "First note")
        self.assertEqual(stringset[0].character_limit, 10)
        # The skipped unit contributes no placeholder and does not consume an
        # order, so the following unit keeps its position.
        self.assertEqual([s.order for s in stringset], [0, 1])
        self.assertEqual(
            template.count(stringset[0].template_replacement), 1
        )
        # It survives verbatim in the template, with no <target> injected.
        self.assertIn(u'<source>Bye</source>', template)
        self.assertNotIn(u'>Bye</target>', template)

    def test_duplicate_unit_id_compiles(self):
        """The skipped duplicate must not desync the compile cursor."""
        content = _wrap(
            u'<unit id="dup"><segment><source>Hi</source></segment></unit>'
            u'<unit id="dup"><segment><source>Bye</source></segment></unit>'
            u'<unit id="after"><segment><source>Tail</source></segment></unit>'
        )
        template, stringset = self.handler.parse(content, is_source=True)
        compiled = self.handler.compile(
            template, _translate(stringset, u"XX")
        )
        targets = ET.fromstring(compiled.encode("utf-8")).findall(
            ".//{urn:oasis:names:tc:xliff:document:2.0}target"
        )
        self.assertEqual([t.text for t in targets], ["XX", "XX"])
        # The duplicate keeps its source and stays target-less.
        self.assertIn(u'<source>Bye</source>', compiled)

    def test_duplicate_unit_id_across_files_is_kept(self):
        """unit/@id only has to be unique within its <file> (XLIFF 2.0 spec),
        so the same id in another <file> is a distinct string."""
        content = (
            u'<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" '
            u'version="2.0" srcLang="en">'
            u'<file id="f1">'
            u'<unit id="dup"><segment><source>Hi</source></segment></unit>'
            u'</file>'
            u'<file id="f2">'
            u'<unit id="dup"><segment><source>Bye</source></segment></unit>'
            u'</file></xliff>'
        )
        _, stringset = self.handler.parse(content, is_source=True)
        self.assertEqual(
            [(s.key, s.context, s.string) for s in stringset],
            [("dup", "f1", "Hi"), ("dup", "f2", "Bye")],
        )

    def test_duplicate_unit_id_on_translation_upload_keeps_the_first(self):
        content = _wrap(
            u'<unit id="dup">'
            u'<segment><source>Hi</source><target>Geia</target></segment>'
            u'</unit>'
            u'<unit id="dup">'
            u'<segment><source>Bye</source><target>Adio</target></segment>'
            u'</unit>'
        )
        _, stringset = self.handler.parse(content, is_source=False)
        self.assertEqual(
            [(s.key, s.string) for s in stringset], [("dup", "Geia")]
        )

    def test_segment_without_source_raises(self):
        content = _wrap(
            u'<unit id="u1"><segment><target>Hi</target></segment></unit>'
        )
        with self.assertRaises(ParseError) as ctx:
            self.handler.parse(content, is_source=True)
        self.assertIn("missing a <source>", six.text_type(ctx.exception))

    def test_plural_missing_other_form_raises(self):
        content = _wrap(
            u'<unit id="u1"><segment>'
            u'<source>{n, plural, one {# thing}}</source>'
            u'</segment></unit>'
        )
        with self.assertRaises(ParseError) as ctx:
            self.handler.parse(content, is_source=True)
        self.assertIn("missing the required 'other'", six.text_type(ctx.exception))


def _wrap(units_xml):
    return (
        u'<?xml version="1.0" encoding="UTF-8"?>\n'
        u'<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" '
        u'version="2.0" srcLang="en">\n'
        u'  <file id="f1">\n'
        u'    {}\n'
        u'  </file>\n'
        u'</xliff>\n'
    ).format(units_xml)


def _translate(stringset, translation):
    for openstring in stringset:
        _set_string(openstring, translation)
    return stringset


def _set_string(openstring, translation):
    for rule in list(openstring._strings.keys()):
        openstring._strings[rule] = translation
    return openstring
