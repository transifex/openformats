import copy
import io
import itertools
import os
import re
import shutil
import tempfile
from uuid import uuid4

from zipfile import ZipFile, ZIP_DEFLATED

from bs4 import BeautifulSoup
from bs4.dammit import EntitySubstitution
from bs4.formatter import XMLFormatter

from openformats.formats.office_open_xml.parser import OfficeOpenXmlHandler
from openformats.handlers import Handler
from openformats.strings import OpenString


class UnsortedAttributes(XMLFormatter):
    def __init__(self, *args, **kwargs):
        super(XMLFormatter, self).__init__(entity_substitution=lambda string: EntitySubstitution.substitute_xml(string).replace('"', '&quot;'))

    def attributes(self, tag):
        for k, v in tag.attrs.items():
            yield k, v


def get_rels_path(sheet_path):
    path = sheet_path.split('/')
    path.insert(-1, '_rels')
    path = '/'.join(path)
    path += '.rels'
    return path


class XlsxFile(object):
    CONTENT_TYPES = "[Content_Types].xml"
    WORKBOOK_CONTENT_TYPE = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
    )
    SHEET_CONTENT_TYPE = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
    )
    COMMENTS_CONTENT_TYPE = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.comments+xml"
    )
    SHARED_STRINGS_CONTENT_TYPE = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"
    )

    def __init__(self, content):
        self.__tmp_folder = "{}/{}".format(tempfile.gettempdir(), uuid4().hex)
        os.mkdir(self.__tmp_folder)

        input_path = self.__tmp_folder + "in.xlsx"

        with io.open(input_path, 'wb') as f:
            f.write(content)

        with ZipFile(input_path, 'r') as z:
            z.extractall(self.__tmp_folder)

        os.remove(input_path)

        self.__filelist = z.namelist()

        self._parse()

    def _parse(self):
        """
        http://officeopenxml.com/SScontentOverview.php
        The possible places that we can find translatable strings in xlsx files are
        1) xl/sharedStrings.xml
        2) or in each sheet that will have inlineStr
        <c r="C4" s="2" t="inlineStr">
            <is>
                <t>my string</t>
            </is>
        </c>
        """
        content_types_file_path = "{}/{}".format(self.__tmp_folder, self.CONTENT_TYPES)
        with io.open(content_types_file_path, "r") as f:
            content_types_file = f.read()
        content_types_soup = BeautifulSoup(content_types_file,'xml')

        workbook_path_internal = content_types_soup.find(
            attrs={'ContentType': self.WORKBOOK_CONTENT_TYPE}
        )['PartName']
        self._workbook_path = "{}{}".format(self.__tmp_folder, workbook_path_internal)

        comment_paths_internal = {
            comment["PartName"]
            for comment in content_types_soup.find_all(
                attrs={'ContentType': self.COMMENTS_CONTENT_TYPE}
            )
        }
        self._comment_paths = {
            "{}{}".format(self.__tmp_folder, comment_path)
            for comment_path in comment_paths_internal
        }

        sheet_items_internal = []
        for sheet_item in content_types_soup.find_all(
                attrs={'ContentType': self.SHEET_CONTENT_TYPE}
        ):
            internal_path = sheet_item.attrs['PartName']
            match = re.search(r"sheet(\d+).xml", internal_path)
            sheet_items_internal.append({
                "path": internal_path,
                "id": int(match.group(1)) if match else None}
            )
        sheet_items_internal = sorted(
            sheet_items_internal,
            key=lambda i: float('inf') if i["id"] is None else int(i["id"])
        )
        self._sheets = {}
        for sheet_item in sheet_items_internal:
            sheet_path = "{}{}".format(self.__tmp_folder, sheet_item["path"])
            sheet_rels_tmp_path = get_rels_path(sheet_path)
            self._sheets[sheet_item["path"]] = {
                "path": sheet_path,
                "rels_path": sheet_rels_tmp_path,
                "id": sheet_item["id"]
            }

        shared_strings_path_internal = content_types_soup.find(
            attrs={'ContentType': self.SHARED_STRINGS_CONTENT_TYPE}
        )["PartName"]
        self._shared_strings_path = "{}{}".format(self.__tmp_folder, shared_strings_path_internal)

    def get_workbook_path(self):
        return self._workbook_path

    def get_sheets(self):
        return self._sheets

    def get_sheet(self, sheet):
        return self._sheets[sheet]

    def get_shared_strings_path(self):
        return self._shared_strings_path

    def get_comment_paths(self):
        return self._comment_paths

    def get_workbook_content(self):
        with open(self.get_workbook_path(), "r") as f:
            workbook_content = f.read()
        return workbook_content

    def set_workbook_content(self, content):
        with open(self.get_workbook_path(), "w") as f:
            f.write(content.encode(formatter=UnsortedAttributes()).decode())

    def get_sheet_content(self, sheet):
        with open(self.get_sheet(sheet)["path"], "r") as f:
            sheet_content = f.read()
        return sheet_content

    def set_sheet_content(self, sheet, content):
        with open(self.get_sheet(sheet)["path"], "w") as f:
            f.write(content.encode(formatter=UnsortedAttributes()).decode())

    def has_rels(self, sheet):
        return os.path.exists(self.get_sheet(sheet)["rels_path"])

    def get_sheet_rels_content(self, sheet):
        with open(self.get_sheet(sheet)["rels_path"], "r") as f:
            sheet_rels = f.read()
        return sheet_rels

    def set_sheet_rels_content(self, sheet, content):
        with open(self.get_sheet(sheet)["rels_path"], "w") as f:
            f.write(content.encode(formatter=UnsortedAttributes()).decode())

    def get_shared_strings_content(self):
        with open(self.get_shared_strings_path(), "r") as f:
            shared_strings_content = f.read()
        return shared_strings_content

    def set_shared_strings_content(self, content):
        with open(self.get_shared_strings_path(), "w") as f:
            f.write(content.encode(formatter=UnsortedAttributes()).decode())

    def delete(self):
        shutil.rmtree(self.__tmp_folder)

    def compress(self):
        output_path = self.__tmp_folder + "/out.xlsx"
        with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as z:
            for filename in self.__filelist:
                z.write(os.path.join(self.__tmp_folder, filename), filename)

        with io.open(output_path, 'rb') as f:
            result = f.read()

        os.remove(output_path)
        return result


def wrap(string, hyperlink=None):
    href = ""
    if hyperlink:
        href = " href='{}'".format(hyperlink)
    return "<tx{}>{}</tx>".format(href, string)


class XlsxUnstructuredHandler(Handler, OfficeOpenXmlHandler):
    PROCESSES_BINARY = True
    EXTRACTS_RAW = False
    name = "XLSX_UNSTRUCTURED"

    @staticmethod
    def _extract_sheet_names(xlsx):
        wordbook_soup = BeautifulSoup(
            xlsx.get_workbook_content(), "xml"
        )
        sheets = wordbook_soup.find_all("sheet")
        sheet_names = []
        for sheet in sheets:
            open_string = OpenString(
                sheet["name"],
                sheet["name"],
            )
            sheet.attrs['txid'] = open_string.string_hash
            sheet_names.append(open_string)
        xlsx.set_workbook_content(wordbook_soup)
        return sheet_names

    def parse(self, content, **kwargs):
        xlsx = XlsxFile(content)

        order = itertools.count()

        sheet_names = self._extract_sheet_names(xlsx)

        shared_strings_soup = BeautifulSoup(xlsx.get_shared_strings_content(), "xml")
        shared_strings = shared_strings_soup.find_all("si")

        extracted_strings = {}

        for sheet_name in sheet_names:
            if sheet_name.string not in extracted_strings:
                extracted_strings[sheet_name.string] = {
                    "sheets": [sheet_name.string],
                }
            elif sheet_name not in extracted_strings[sheet_name.string]["sheets"]:
                extracted_strings[sheet_name.string]["sheets"].append(sheet_name.string)

        sheet_index = -1
        for sheet, sheet_details in xlsx.get_sheets().items():
            sheet_index += 1
            sheet_name = sheet_names[sheet_index].string

            sheet_soup = BeautifulSoup(xlsx.get_sheet_content(sheet), "xml")
            sheet_rels_soup = None
            if xlsx.has_rels(sheet):
                sheet_rels_soup = BeautifulSoup(xlsx.get_sheet_rels_content(sheet), "xml")
            """
            we parse cells with possible translatable text
            - `s` is cells that there strins come from sharedStrings
              if an s cell has a hyperlink we make this text inline so that it is
              translatable autonomously otherwise we can't provide different
              translations
            - `inlineStr` are cells with strings that are expecetily marked to not use
              sharedStrings
            - `str` cells contain values calculated from formulas. in our case we care
              only about HYPERLINKS("link", "display_text")
              potentially more formulas can be parsed but 
            """
            sheet_text_cells = sheet_soup.find_all(
                "c", attrs={"t": ["s", "inlineStr", "str"]}
            )
            hyperlink_map = {}
            if sheet_rels_soup:
                relationships = sheet_rels_soup.find_all(
                    "Relationship",
                    attrs={"TargetMode": "External"}
                ) or []

                rels_map = {
                    relationship.attrs["Id"]: relationship.attrs["Target"]
                    for relationship in relationships
                }
                for hyperlink in sheet_soup.find_all("hyperlink"):
                    r_id = hyperlink["r:id"] if hyperlink.has_attr("r:id") else None
                    if r_id and r_id in rels_map:
                        hyperlink_map[hyperlink.attrs["ref"]] = rels_map[r_id]

            for sheet_text_cell in sheet_text_cells:
                cell_ref = sheet_text_cell.attrs["r"]
                cell_hyper_link = hyperlink_map.get(cell_ref)

                shared_string_element = None
                if all([
                    sheet_text_cell.has_attr("t"),
                    sheet_text_cell.attrs["t"] == 's',
                    sheet_text_cell.v
                ]):
                    shared_string_index = int(sheet_text_cell.v.text)
                    shared_string_element = shared_strings[shared_string_index]

                if cell_hyper_link and shared_string_element:
                    sheet_text_cell.v.replace_with(copy.copy(shared_string_element))
                    sheet_text_cell.si.name = "is"
                    find_string_from = sheet_text_cell
                    sheet_text_cell.attrs["t"] = "inlineStr"
                elif shared_string_element:
                    find_string_from = shared_string_element
                else:
                    find_string_from = sheet_text_cell

                string = None
                if all([
                    sheet_text_cell.has_attr("t"),
                    sheet_text_cell.attrs["t"] == "str",
                    sheet_text_cell.f,
                ]):
                    link_content = sheet_text_cell.f.text
                    match = re.search(r'HYPERLINK\("(.*?)","(.*?)"\)', link_content)
                    link, text = match.groups() if match else (None, None)
                    if link and text:
                        string = wrap(text, link)
                else:
                    t_strings = find_string_from.find_all("t")
                    t_strings_len = len(t_strings)

                    string_parts = []
                    for t_string in t_strings:
                        text_string = t_string.text
                        text = wrap(text_string) if t_strings_len > 1 else text_string
                        string_parts.append(text)
                    string = "".join(string_parts)

                    if cell_hyper_link:
                        string = wrap(string, cell_hyper_link)

                if string:
                    open_string_tmp = OpenString(
                        key=string, string_or_strings=string
                    )
                    find_string_from.attrs['txid'] = open_string_tmp.string_hash
                    if open_string_tmp.string not in extracted_strings:
                        extracted_strings[string] = {
                            "sheets": [sheet_name],
                        }
                    elif sheet_name not in extracted_strings[string]["sheets"]:
                        extracted_strings[string]["sheets"].append(sheet_name)

            xlsx.set_sheet_content(sheet, sheet_soup)
        xlsx.set_shared_strings_content(shared_strings_soup)

        all_strings = []

        for string, string_details in extracted_strings.items():
            developer_comment = ", ".join(string_details.get("sheets", []))
            open_string = OpenString(
                string,
                string,
                developer_comment=developer_comment,
            )
            open_string.order = next(order)
            all_strings.append(open_string)

        template = xlsx.compress()

        xlsx.delete()
        return template, all_strings

    @staticmethod
    def _prepare_string(input_list, n):
        cleaned_strings = []
        spaces = 0
        for i, string in enumerate(input_list):
            tmp_string = string
            if len(string.strip()) == 0:
                continue
            elif len(string) > 0 and not string.strip():
                spaces = len(string)
            else:
                if spaces:
                    spaces_text = {spaces * " "}
                    if len(cleaned_strings) > 0:
                        tmp_string = "{}{}".format(spaces_text, string)
                    else:
                        tmp_string = "{}{}".format(string, spaces_text)
                    spaces=0
            if len(cleaned_strings) >= n:
                cleaned_strings[-1] += tmp_string
            else:
                cleaned_strings.append(tmp_string)

        return cleaned_strings

    def _compile_workbook(self, xlsx, stringset):
        workbook_soup = BeautifulSoup(
            xlsx.get_workbook_content(), "xml"
        )
        sheets = workbook_soup.find_all("sheet")
        for sheet in sheets:
            txid = sheet.attrs.get("txid")
            if not txid:
                continue
            open_string = stringset.get(txid)

            if not open_string:
                continue

            sheet.attrs["name"] = open_string.string
            sheet.attrs.pop("txid", None)
        xlsx.set_workbook_content(workbook_soup)


    def compile(self, template, stringset, **kwargs):
        is_rtl = kwargs.get('is_rtl', False)
        stringset = {
            string.string_hash: string for string in stringset
        }
        xlsx = XlsxFile(template)

        shared_strings_soup = BeautifulSoup(xlsx.get_shared_strings_content(), "xml")
        shared_strings = shared_strings_soup.find_all("si")

        self._compile_workbook(xlsx, stringset)
        for sheet in xlsx.get_sheets():
            sheet_soup = BeautifulSoup(xlsx.get_sheet_content(sheet), "xml")
            sheet_rels_soup = None
            if xlsx.has_rels(sheet):
                sheet_rels_soup = BeautifulSoup(
                    xlsx.get_sheet_rels_content(sheet), "xml"
                )

            if is_rtl is not None:
                sheet_view = sheet_soup.find("sheetView")
                if sheet_view:
                    sheet_view.attrs["rightToLeft"] = is_rtl

            sheet_text_cells = sheet_soup.find_all(
                "c",
                attrs={"t": ["s", "inlineStr", "str"]}
            )

            hyperlink_map = {}
            if sheet_rels_soup:
                relationships = sheet_rels_soup.find_all(
                    "Relationship",
                    attrs={"TargetMode": "External"}
                ) or []

                rels_map = {
                    relationship.attrs["Id"]: relationship.attrs["Target"]
                    for relationship in relationships
                }
                for hyperlink in sheet_soup.find_all("hyperlink"):
                    r_id = hyperlink["r:id"] if hyperlink.has_attr("r:id") else None
                    if r_id and r_id in rels_map:
                        hyperlink_map[hyperlink.attrs["ref"]] = r_id

            for sheet_text_cell in sheet_text_cells:
                txid = sheet_text_cell.attrs.get("txid")
                replace_string_to = None

                if txid:
                    replace_string_to = sheet_text_cell

                if all([
                    not txid,
                    sheet_text_cell.has_attr("t"),
                    sheet_text_cell.attrs["t"] == 's',
                ]):
                    shared_string_index = int(sheet_text_cell.v.text)
                    shared_string_element = shared_strings[shared_string_index]
                    if shared_string_element.has_attr("txid"):
                        txid = shared_string_element.attrs["txid"]
                        replace_string_to = shared_string_element

                if not replace_string_to:
                    continue

                open_string = stringset.get(txid)

                if not open_string:
                    continue

                cell_ref = sheet_text_cell.attrs["r"]

                translation_string = open_string.string
                escaped_translation_string = self._escape_xml(translation_string)

                """
                some examples of transifex translations would be
                - part1
                - <tx>part1</tx><tx>part2</tx>
                - <tx href='app.transifex.com'><tx>part1</tx><tx>part2</tx></tx>
                """
                translation_soup = BeautifulSoup(
                    u'<wrapper>{}</wrapper>'.format(escaped_translation_string), 'xml',
                )
                translation_hyperlink = translation_soup.find(
                    lambda tag: tag.has_attr("href")
                )
                translation_parts = translation_soup.find_all(text=True)

                target_url = None
                if translation_hyperlink:
                    target_url = translation_hyperlink.attrs["href"]

                cell_hyper_link_id = hyperlink_map.get(cell_ref)
                if target_url and cell_hyper_link_id:
                    rel = sheet_rels_soup.find(
                        "Relationship",
                        attrs={"Id": cell_hyper_link_id, "TargetMode": "External"}
                    )
                    rel.attrs["Target"] = target_url

                if all([
                    sheet_text_cell.has_attr("t"),
                    sheet_text_cell.attrs["t"] == "str",
                    sheet_text_cell.f,
                ]):
                    link_content = sheet_text_cell.f.text
                    match = re.search(r'HYPERLINK\("(.*?)","(.*?)"\)', link_content)
                    link, text = match.groups() if match else (None, None)
                    if link and text:
                        translation = "".join(translation_parts)
                        if target_url:
                            sheet_text_cell.f.string = (
                                f'HYPERLINK("{target_url}","{translation}")'
                            )
                        else:
                            sheet_text_cell.f.string = (
                                f'HYPERLINK("{link}","{translation}")'
                            )

                else:
                    t_strings = replace_string_to.find_all("t")
                    t_strings_len = len(t_strings)

                    translation_parts_cleaned = self._prepare_string(
                        translation_parts, t_strings_len
                    )

                    for t_string in t_strings:
                        translation = (
                            translation_parts_cleaned.pop(0)
                            if translation_parts_cleaned
                            else None
                        )

                        if not translation:
                            t_string.decompose()
                            continue
                        t_string.string = translation
                replace_string_to.attrs.pop("txid", None)
            xlsx.set_sheet_content(sheet, sheet_soup)
            xlsx.set_shared_strings_content(shared_strings_soup)
            if xlsx.has_rels(sheet):
                xlsx.set_sheet_rels_content(sheet, sheet_rels_soup)

        result = xlsx.compress()
        xlsx.delete()
        return result

