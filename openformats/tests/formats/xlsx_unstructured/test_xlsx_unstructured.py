# -*- coding: utf-8 -*-
from copy import copy
from unittest import mock
import unittest
import uuid

from openformats.formats.xlsx_unstructured import XlsxUnstructuredHandler, XlsxFile
from openformats.strings import OpenString


class XlsxTestCase(unittest.TestCase):
    TESTFILE_BASE = "openformats/tests/formats/xlsx_unstructured/files"

    def setUp(self):
        self.maxDiff = None

    def load_file(self, file_name):
        path = "{}/{}".format(self.TESTFILE_BASE, file_name)
        with open(path, "rb") as f:
            content = f.read()
        return content

    def write_file(self, file_name, content):
        path = "{}/{}".format(self.TESTFILE_BASE, file_name)
        with open(path, "wb") as f:
            f.write(content)
        return

    def assert_open_string(self, open_string, data):
        self.assertEqual(open_string.string_hash, data.get("string_hash"))
        self.assertEqual(open_string.string, data.get("string"))

        if "order" in data:
            self.assertEqual(open_string.order, data.get("order"))

        self.assertEqual(
            open_string.pluralized, data.get("pluralized", open_string.pluralized)
        )
        self.assertEqual(
            open_string.developer_comment,
            data.get("developer_comment", open_string.developer_comment),
        )
        self.assertEqual(
            open_string.template_replacement,
            data.get(
                "template_replacement",
                open_string.template_replacement,
            ),
        )
        self.assertEqual(open_string.tags, data.get("tags", open_string.tags))

    @mock.patch("openformats.formats.xlsx_unstructured.uuid4")
    def test_xlsx_file(self, m_uuid):
        my_uuid = uuid.uuid4()
        m_uuid.return_value = my_uuid

        content = self.load_file("example.xlsx")
        xlsx = XlsxFile(content)
        sheets = xlsx.get_sheets()

        sheet_path = "/tmp/{}/xl/worksheets/sheet{}.xml"
        sheet_rels_path = "/tmp/{}/xl/worksheets/_rels/sheet{}.xml.rels"
        self.assertEqual(
            sheets,
            {
                "/xl/worksheets/sheet1.xml": {
                    "path": sheet_path.format(my_uuid.hex, 1),
                    "rels_path": sheet_rels_path.format(my_uuid.hex, 1),
                    "id": 1,
                },
                "/xl/worksheets/sheet2.xml": {
                    "path": sheet_path.format(my_uuid.hex, 2),
                    "rels_path": sheet_rels_path.format(my_uuid.hex, 2),
                    "id": 2,
                },
                "/xl/worksheets/sheet3.xml": {
                    "path": sheet_path.format(my_uuid.hex, 3),
                    "rels_path": sheet_rels_path.format(my_uuid.hex, 3),
                    "id": 3,
                },
                "/xl/worksheets/sheet4.xml": {
                    "path": sheet_path.format(my_uuid.hex, 4),
                    "rels_path": sheet_rels_path.format(my_uuid.hex, 4),
                    "id": 4,
                },
                "/xl/worksheets/sheet5.xml": {
                    "path": sheet_path.format(my_uuid.hex, 5),
                    "rels_path": sheet_rels_path.format(my_uuid.hex, 5),
                    "id": 5,
                },
                "/xl/worksheets/sheet6.xml": {
                    "path": sheet_path.format(my_uuid.hex, 6),
                    "rels_path": sheet_rels_path.format(my_uuid.hex, 6),
                    "id": 6,
                },
            },
        )

        self.assertEqual(
            xlsx.get_workbook_path(), "/tmp/{}/xl/workbook.xml".format(my_uuid.hex)
        )

        self.assertEqual(
            xlsx.get_shared_strings_path(),
            "/tmp/{}/xl/sharedStrings.xml".format(my_uuid.hex),
        )

        self.assertEqual(
            xlsx.get_comment_paths(), {"/tmp/{}/xl/comments5.xml".format(my_uuid.hex)}
        )

    def test_xlsx_handler_parse(self):
        content = self.load_file("example.xlsx")
        xlsx_handler = XlsxUnstructuredHandler()
        template, stringset = xlsx_handler.parse(content)
        self.assertIsNotNone(template)
        self.assertEqual(len(stringset), 12)
        self.assert_open_string(
            stringset[0],
            {
                "string_hash": mock.ANY,
                "string": "Sheet1",
                "order": 0,
                "developer_comments": "Sheet 1",
            },
        )
        self.assert_open_string(
            stringset[1],
            {
                "string_hash": mock.ANY,
                "string": "Sheet2",
                "order": 1,
                "developer_comment": "Sheet2",
            },
        )
        self.assert_open_string(
            stringset[2],
            {
                "string_hash": mock.ANY,
                "string": "Sheet3",
                "order": 2,
                "developer_comment": "Sheet3",
            },
        )
        self.assert_open_string(
            stringset[3],
            {
                "string_hash": mock.ANY,
                "string": "Sheet4",
                "order": 3,
                "developer_comment": "Sheet4",
            },
        )
        self.assert_open_string(
            stringset[4],
            {
                "string_hash": mock.ANY,
                "string": "Sheet5",
                "order": 4,
                "developer_comment": "Sheet5",
            },
        )
        self.assert_open_string(
            stringset[5],
            {
                "string_hash": mock.ANY,
                "string": "Sheet6",
                "order": 5,
                "developer_comment": "Sheet6",
            },
        )
        self.assert_open_string(
            stringset[6],
            {
                "string_hash": mock.ANY,
                "string": "<tx>    I am a file  </tx><tx>“bold”</tx>",
                "order": 6,
                "developer_comment": "Sheet1",
            },
        )
        self.assert_open_string(
            stringset[7],
            {
                "string_hash": mock.ANY,
                "string": "I have two sheets",
                "order": 7,
                "developer_comment": "Sheet2, Sheet4",
            },
        )
        self.assert_open_string(
            stringset[8],
            {
                "string_hash": mock.ANY,
                "string": "<tx href='http://app.transifex.com/'>and a cell with a link</tx>",
                "order": 8,
                "developer_comment": "Sheet3",
            },
        )
        self.assert_open_string(
            stringset[9],
            {
                "string_hash": mock.ANY,
                "string": "And an inline string",
                "order": 9,
                "developer_comment": "Sheet4",
            },
        )
        self.assert_open_string(
            stringset[10],
            {
                "string_hash": mock.ANY,
                "string": "and a comment",
                "order": 10,
                "developer_comment": "Sheet5",
            },
        )
        self.assert_open_string(
            stringset[11],
            {
                "string_hash": mock.ANY,
                "string": "<tx href='https://www.google.com'>FormulaLink</tx>",
                "order": 11,
                "developer_comment": "Sheet6",
            },
        )

    def test_xlsx_handler_compilation_reverse(self):
        content = self.load_file("example.xlsx")
        xlsx_handler = XlsxUnstructuredHandler()
        template, stringset = xlsx_handler.parse(content)

        new_stringset = []
        for string in stringset:
            new_stringset.append(OpenString(string.key, string.string + " New"))

        compiled_content = xlsx_handler.compile(template, new_stringset)
        reparsed_template, reparsed_stringset = xlsx_handler.parse(compiled_content)

        self.assertIsNotNone(reparsed_template)
        self.assertEqual(len(reparsed_stringset), 12)
        self.assert_open_string(
            reparsed_stringset[0],
            {"string_hash": mock.ANY, "string": "Sheet1 New", "order": 0},
        )
        self.assert_open_string(
            reparsed_stringset[1],
            {"string_hash": mock.ANY, "string": "Sheet2 New", "order": 1},
        )
        self.assert_open_string(
            reparsed_stringset[2],
            {"string_hash": mock.ANY, "string": "Sheet3 New", "order": 2},
        )
        self.assert_open_string(
            reparsed_stringset[3],
            {"string_hash": mock.ANY, "string": "Sheet4 New", "order": 3},
        )
        self.assert_open_string(
            reparsed_stringset[4],
            {"string_hash": mock.ANY, "string": "Sheet5 New", "order": 4},
        )
        self.assert_open_string(
            reparsed_stringset[5],
            {"string_hash": mock.ANY, "string": "Sheet6 New", "order": 5},
        )
        self.assert_open_string(
            reparsed_stringset[6],
            {
                "string_hash": mock.ANY,
                "string": "<tx>    I am a file  </tx><tx>“bold” New</tx>",
                "order": 6,
            },
        )
        self.assert_open_string(
            reparsed_stringset[7],
            {"string_hash": mock.ANY, "string": "I have two sheets New", "order": 7},
        )
        self.assert_open_string(
            reparsed_stringset[8],
            {
                "string_hash": mock.ANY,
                "string": "<tx href='http://app.transifex.com/'>and a cell with a link New</tx>",
                "order": 8,
            },
        )
        self.assert_open_string(
            reparsed_stringset[9],
            {"string_hash": mock.ANY, "string": "And an inline string New", "order": 9},
        )
        self.assert_open_string(
            reparsed_stringset[10],
            {"string_hash": mock.ANY, "string": "and a comment New", "order": 10},
        )
        self.assert_open_string(
            reparsed_stringset[11],
            {
                "string_hash": mock.ANY,
                "string": "<tx href='https://www.google.com'>FormulaLink New</tx>",
                "order": 11,
            },
        )

    def test_strings_with_less_tx_tags(self):
        content = self.load_file("example.xlsx")
        xlsx_handler = XlsxUnstructuredHandler()
        template, stringset = xlsx_handler.parse(content)

        self.assert_open_string(
            stringset[6],
            {
                "string_hash": mock.ANY,
                "string": "<tx>    I am a file  </tx><tx>“bold”</tx>",
            },
        )

        stringset[6] = OpenString(stringset[6].key, "no_tags")
        compiled_file = xlsx_handler.compile(template, stringset)
        template, stringset = xlsx_handler.parse(compiled_file)

        self.assert_open_string(
            stringset[6], {"string_hash": mock.ANY, "string": "no_tags"}
        )

    def test_extract_compile_hyperlink_formulas(self):
        content = self.load_file("example.xlsx")
        xlsx_handler = XlsxUnstructuredHandler()
        template, stringset = xlsx_handler.parse(content)

        self.assert_open_string(
            stringset[11],
            {
                "string_hash": mock.ANY,
                "string": "<tx href='https://www.google.com'>FormulaLink</tx>",
                "order": 11,
            },
        )

        stringset[11] = OpenString(
            stringset[11].key,
            "<tx href='https://www.google.com'>FormulaLink</tx> <tx>something else</tx>",
        )
        compiled_file = xlsx_handler.compile(template, stringset)
        template, stringset = xlsx_handler.parse(compiled_file)

        self.assert_open_string(
            stringset[11],
            {
                "string_hash": mock.ANY,
                "string": "<tx href='https://www.google.com'>FormulaLink something else</tx>",
                "order": 11,
            },
        )

        stringset[11] = OpenString(stringset[11].key, "no hyper link")
        compiled_file = xlsx_handler.compile(template, stringset)
        template, stringset = xlsx_handler.parse(compiled_file)

        self.assert_open_string(
            stringset[11],
            {
                "string_hash": mock.ANY,
                "string": "<tx href='https://www.google.com'>no hyper link</tx>",
                "order": 11,
            },
        )
