import io
import itertools
import os
import re
import shutil
import tempfile
import uuid
from zipfile import ZIP_DEFLATED, ZipFile

import six
from bs4 import BeautifulSoup
from openformats.handlers import Handler
from openformats.formats.office_open_xml.parser import OfficeOpenXmlHandler


class DocxFile(object):
    """
    A class used to wrap and expose the internals of a .docx file

    A docx file is a zipped file that when unzipped,
    generates a similar file/folder structure:
        /_rels/
            .rels
            [Content_Types].xml
            ...
        /word/
            document.xml
            /_rels/
                document.xml.rels
            ...

    The parts that are in interesting are:
        * word/document.xml: that contains all(*) the textual content
          that exists in the document
        * word/_rels/document.xml.rels document's relationship follows the rule
    for relationship files: `{document path}/_rels/{document filename}.rels`

    The structure of the main file is as following:
    ```
    <w:document>
        <w:body>
            <w:p>
                ...
                <w:r>
                    ...
                    <w:t xml:space="preserve">hello</w:t>
                    ...
                </w:r>
                ...
                <w:r>
                    ...
                    <w:t xml:space="preserve">world</w:t>
                    ...
                </w:r>
                ...
            </w:p>
            ...
            <w:p>
                <w:hyperlink r:id="rId6">
                    ...
                    <w:r>
                        ...
                        <w:t xml:space="preserve">this is a link</w:t>
                        ...
                    </w:r>
                    ...
                </w:hyperlink>
            </w:p>
        </w:body>
    </w:document>
    ```

    The text is located at `<w:t>` tags.

    The structure of the main document's relationships is as following:
    ```
    <Relationships>
        ...
        <Relationship Id="rId6" Target="https://www.transifex.com/"
                      TargetMode="External"/>
        ...
    </Relationships>
    ```
    """

    def __init__(self, content):
        self.__tmp_folder = "{}/{}".format(
            tempfile.gettempdir(), uuid.uuid4().hex
        )
        os.mkdir(self.__tmp_folder)

        docx_path = '{}/{}.docx'.format(self.__tmp_folder, 'in')
        with io.open(docx_path, 'wb') as f:
            f.write(content)

        with ZipFile(docx_path, 'r') as z:
            z.extractall(self.__tmp_folder)

        self.__filelist = z.namelist()

        os.remove(docx_path)

        base_rels_path = '{}/{}'.format(self.__tmp_folder, '_rels/.rels')
        with io.open(base_rels_path, 'r') as f:
            base_rels = f.read()

        if base_rels.startswith("\ufeff"):
            # Remove BOM
            base_rels = base_rels.replace("\ufeff", "")

        document_relative_path = next((
            relationship
            for relationship in (BeautifulSoup(base_rels, 'xml').
                                 find_all(attrs={'Target': True}))
            if relationship.attrs.get('Type').endswith('/officeDocument')
        )).attrs['Target']

        self.__document_path = '{}/{}'.format(
            self.__tmp_folder, document_relative_path
        )
        self.__document = None

        document_folder, document_file = os.path.split(document_relative_path)
        self.__document_rels_path = '{}/{}/_rels/{}.rels'.format(
            self.__tmp_folder, document_folder, document_file
        )
        self.__document_rels = None

    def get_document(self):
        if self.__document is None:
            with io.open(self.__document_path, 'r') as f:
                self.__document = f.read()

            if self.__document.startswith("\ufeff"):
                # Remove BOM
                self.__document = self.__document.replace("\ufeff", "")

        return self.__document

    def set_document(self, document):
        self.__document = document

        with io.open(self.__document_path, 'w') as f:
            f.write(document)

    def get_document_rels(self):
        if self.__document_rels is None:
            with io.open(self.__document_rels_path, 'r') as f:
                self.__document_rels = f.read()

        return self.__document_rels

    def set_document_rels(self, document_rels):
        self.__document_rels = document_rels

        with io.open(self.__document_rels_path, 'w') as f:
            f.write(document_rels)

    def compress(self):
        docx_path = '{}/{}.docx'.format(self.__tmp_folder, 'out')

        with ZipFile(docx_path, "w", compression=ZIP_DEFLATED) as z:
            for filename in self.__filelist:
                z.write(os.path.join(self.__tmp_folder, filename), filename)

        with io.open(docx_path, 'rb') as f:
            result = f.read()

        os.remove(docx_path)

        return result

    def delete(self):
        shutil.rmtree(self.__tmp_folder)


class DocxHandler(Handler, OfficeOpenXmlHandler):
    PROCESSES_BINARY = True
    EXTRACTS_RAW = False
    name = "DOCX"
    TEXT_ELEMENT_TAG = "w:t"

    @classmethod
    def get_hyperlink_url(cls, element, document_rels):
        run_parent = element.find_parent('w:r').parent

        if run_parent.name == 'hyperlink':
            rel = document_rels.find(
                attrs={"Id": run_parent.attrs.get('r:id')}
            )
            if rel and rel.attrs.get('TargetMode') == 'External':
                return rel.attrs['Target']

        return None

    @classmethod
    def set_hyperlink_url(cls, element, document_rels, url):
        run_parent = element.find_parent('w:r').parent

        if run_parent.name == 'hyperlink':
            rel = document_rels.find(
                attrs={"Id": run_parent.attrs.get('r:id')}
            )
            if rel and rel.attrs['TargetMode'] == 'External':
                rel.attrs['Target'] = url

    @classmethod
    def create_hyperlink_url(cls, element, document_rels, url):
        max_rid = max([
            int(re.findall(r'\d+', e["Id"])[0])
            for e in document_rels.find_all(attrs={"Id": True})
        ])

        rid = "rId{}".format(max_rid+1)
        hyperlink_rel = document_rels.new_tag(
            "Relationship",
            TargetMode="External",
            Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",  # noqa
            Target=url,
            Id=rid
        )
        document_rels.Relationships.append(hyperlink_rel)
        hyperlink = document_rels.new_tag(
            "w:hyperlink",
            **{"r:id": rid}
        )
        contents = element.find_parent('w:r').replace_with(hyperlink)
        hyperlink.append(contents)

    @classmethod
    def remove_hyperlink(cls, text_element):
        text_element.parent.parent.unwrap()

    @classmethod
    def remove_text_element(cls, text_element):
        if text_element.find_parent('w:r') is not None:
            run_parent = text_element.find_parent('w:r').parent
            if run_parent.name == 'hyperlink':
                return text_element.find_parent('w:hyperlink').decompose()

        return text_element.decompose()

    @classmethod
    def set_rtl_orientation(cls, paragraph):
        soup = BeautifulSoup("", "xml")
        ppr_tags = paragraph.find_all("w:pPr")

        if len(ppr_tags) == 0:
            pPr = soup.new_tag("w:pPr")
            paragraph.append(pPr)
            ppr_tags = [pPr]

        for ppr_tag in ppr_tags:
            if ppr_tag.bidi is not None:
                ppr_tag.bidi.decompose()
            bidi_tag = soup.new_tag("w:bidi", **{"w:val": "1"})
            ppr_tag.append(bidi_tag)

        rpr_tags = paragraph.find_all("w:rPr")
        for rpr_tag in rpr_tags:
            if rpr_tag.rtl is not None:
                rpr_tag.rtl.decompose()
            rtl = soup.new_tag("w:rtl", **{"w:val": "1"})
            rpr_tag.append(rtl)

    @classmethod
    def set_rtl_orientation_tables(cls, tbl, soup):
        """
        Ensure <w:bidiVisual/> is present under the table's <w:tblPr>.
        """
        tblPr = tbl.find("w:tblPr")
        if tblPr is None:
            tblPr = soup.new_tag("w:tblPr")
            tbl.insert(0, tblPr)

        if tblPr.find("w:bidiVisual") is None:
            tblPr.append(soup.new_tag("w:bidiVisual"))

    def parse(self, content, **kwargs):
        """
        We will segment the text by paragraph `<w:p>` as this
        is defined in the docx structure.

        For all the text `<w:t>` inside a paragraph,
        we use tag separators `<tx>`, in order to denote
        text style changes (normal->bold, bold->italic, 10px->14px etc)
        or hyperlinks that are present in the text.

        In each paragraph we will attach the hash of the openstring
        as `txid` attribute in order to be able to match when
        compilation takes place.
        """
        docx = DocxFile(content)

        soup = BeautifulSoup(docx.get_document(), 'xml')
        rels_soup = BeautifulSoup(docx.get_document_rels(), 'xml')

        stringset = []
        order = itertools.count()
        for paragraph in soup.find_all('w:p'):
            open_string = self.parse_paragraph(paragraph, rels_soup)
            if not open_string:
                continue

            open_string.order = next(order)
            stringset.append(open_string)

        docx.set_document(six.text_type(soup))

        template = docx.compress()
        docx.delete()
        return template, stringset

    def compile(self, template, stringset, **kwargs):
        stringset = {
            string.string_hash: string for string in stringset
        }
        docx = DocxFile(template)
        soup = BeautifulSoup(docx.get_document(), 'xml')
        rels_soup = BeautifulSoup(docx.get_document_rels(), 'xml')
        is_rtl = kwargs.get('is_rtl', False)

        for paragraph in soup.find_all('w:p'):
            self.compile_paragraph(
                paragraph, rels_soup, stringset, is_rtl=is_rtl
            )

        if is_rtl:
            for tbl in soup.find_all("w:tbl"):
                self.set_rtl_orientation_tables(tbl, soup)

        docx.set_document(six.text_type(soup))
        docx.set_document_rels(six.text_type(rels_soup))

        result = docx.compress()
        docx.delete()
        return result
