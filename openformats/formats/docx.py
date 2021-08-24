import io
import itertools
import os
import re
import shutil
import tempfile
import uuid
from collections import defaultdict
from zipfile import ZIP_DEFLATED, ZipFile

import six
from bs4 import BeautifulSoup
from copy import deepcopy
from openformats.handlers import Handler
from openformats.strings import OpenString


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


class DocxHandler(Handler):
    PROCESSES_BINARY = True
    EXTRACTS_RAW = False
    name = "DOCX"

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
            paragraph_text = []
            text_elements = paragraph.find_all('w:t')
            if not text_elements:
                continue

            text_elements_count = len(text_elements)

            open_hyperlink = None
            leading_spaces = 0
            for index, text_element in enumerate(text_elements):
                text = text_element.text
                # skip text elements that contain no text
                # and prepend leading whitespace to the next string
                if not text.strip():
                    leading_spaces += len(text) - len(text.strip())
                    continue
                else:
                    text = u"".join([u" "*leading_spaces, text])
                    leading_spaces = 0

                hyperlink_url = self.get_hyperlink_url(
                    text_element, rels_soup
                )

                if all([
                    text_elements_count == 2,
                    not hyperlink_url or hyperlink_url == open_hyperlink
                ]) or all([
                    index > 0,
                    index < text_elements_count - 1,
                    not hyperlink_url or hyperlink_url == open_hyperlink
                ]):
                    # skip surrounding text with tags if:
                    #   * first element
                    #   * last element
                    #   * opening hyperlink (we will add the tx tag later)
                    text = u'<tx>{}</tx>'.format(text)

                if hyperlink_url and not open_hyperlink:
                    # open an a tag
                    text = u'<tx href="{}">{}'.format(
                        hyperlink_url, text
                    )
                    open_hyperlink = hyperlink_url

                if not hyperlink_url and open_hyperlink:
                    # close a tag if open
                    text = u'</tx>{}'.format(text)
                    open_hyperlink = None

                if hyperlink_url and open_hyperlink:
                    if hyperlink_url != open_hyperlink:
                        # close and open a new tag
                        text = u'</tx><tx href="{}">{}'.format(
                            hyperlink_url, text
                        )
                        open_hyperlink = hyperlink_url

                paragraph_text.append(text)

            if open_hyperlink:
                # close the open tag
                paragraph_text.append(u'</tx>')
                open_hyperlink = None

            paragraph_text = u''.join(paragraph_text)
            if not paragraph_text.strip():
                continue

            open_string = OpenString(
                paragraph_text,
                paragraph_text,
                order=next(order)
            )

            stringset.append(open_string)
            paragraph.attrs['txid'] = open_string.string_hash

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

        for paragraph in soup.find_all('w:p'):
            text_elements = paragraph.find_all('w:t')
            if not text_elements:
                continue

            txid = paragraph.attrs.get('txid')

            if not txid:
                continue

            if stringset.get(txid, None) is None:
                continue

            translation = stringset[txid].string
            translation = self._escape_xml(translation)

            translation_soup = BeautifulSoup(
                u'<wrapper>{}</wrapper>'.format(translation), 'xml',
            ).find_all(text=True)

            leading_spaces = 0

            added_hl_text_elements = defaultdict(list)
            deleted_hl_text_elements = defaultdict(list)

            for index, text_element in enumerate(text_elements):
                text = six.text_type(text_element.text)
                # detect text elements that contain no text
                # and remove leading whitespace from the next string
                if not text.strip():
                    leading_spaces = len(text) - len(text.strip())
                    continue
                else:
                    hyperlink_url = self.get_hyperlink_url(
                        text_element, rels_soup
                    )
                    # the text parts of the translation are less that the
                    # text parts of the document, so we will just remove
                    # any excessing part from the document
                    if len(translation_soup) == 0:
                        if hyperlink_url:
                            text_element.find_parent('w:hyperlink').decompose()
                        else:
                            text_element.decompose()
                        continue
                    translation_part = translation_soup.pop(0)
                    translation = six.text_type(translation_part)
                    if not translation[:leading_spaces].strip():
                        translation = translation[leading_spaces:]
                    leading_spaces = 0

                # the text parts of the translation are more that the
                # text parts of the document, so we will compress the
                # remaining translation parts into one string
                if (index == len(text_elements) - 1 and
                        len(translation_soup) > 0):
                    translation = "".join(
                        [translation] +
                        [six.text_type(t) for t in translation_soup]
                    )

                # attempt to find a parent containing `href` attribute
                # in order to extract the potential hyperlink url.
                translation_hyperlink_url = getattr(
                    translation_part.find_parent(attrs={'href': True}
                ), 'attrs', {}).get('href', None)

                # Edit in place hyperlink url
                if hyperlink_url and translation_hyperlink_url:
                    self.set_hyperlink_url(
                        text_element, rels_soup, translation_hyperlink_url
                    )

                # remove hyperlink from source docx
                if hyperlink_url and not translation_hyperlink_url:
                    text_element.parent.parent.unwrap()
                    deleted_hl_text_elements[hyperlink_url].append(
                        text_element)

                # create a new hyperlink
                if not hyperlink_url and translation_hyperlink_url:
                    self.create_hyperlink_url(
                        text_element, rels_soup, translation_hyperlink_url
                    )
                    added_hl_text_elements[translation_hyperlink_url].append(
                        text_element)

                text_element.clear()
                text_element.insert(0, translation)

            def _modify_text_element_rpr_tag_contents(te, contents):
                rpr = te.parent.rPr
                color = [c for c in contents if c.name == 'color']
                underline = [c for c in contents if c.name == 'u']

                if rpr.color:
                    rpr.color.extract()
                if color:
                    rpr.append(color[0])
                if rpr.u:
                    rpr.u.extract()
                if underline:
                    rpr.append(underline[0])

            if len(added_hl_text_elements) == len(deleted_hl_text_elements):
                for added_url, deleted_url in zip(
                    added_hl_text_elements.keys(),
                    deleted_hl_text_elements.keys()
                ):
                    added_rpr = [
                        te.parent.rPr for te in added_hl_text_elements[added_url]
                    ][0]
                    added_rpr_copy = deepcopy(added_rpr)
                    deleted_rpr = [
                        te.parent.rPr for te in \
                            deleted_hl_text_elements[deleted_url]
                    ][0]

                    for te in added_hl_text_elements[added_url]:
                        _modify_text_element_rpr_tag_contents(
                            te, deleted_rpr.contents)
                    for te in deleted_hl_text_elements[deleted_url]:
                        _modify_text_element_rpr_tag_contents(
                            te, added_rpr_copy.contents)

        docx.set_document(six.text_type(soup))
        docx.set_document_rels(six.text_type(rels_soup))

        result = docx.compress()
        docx.delete()
        return result

    @staticmethod
    def _escape_xml(translation):
        """ Do escaping: BeautifulSoup doesn't like unescaped '&' or '<' in its
            input. We do expect some '<tx>' and `</tx>` so we first replace
            these tags to placeholders, do the escaping and restore them.
        """
        return translation.\
            replace(u"<tx", u"__TX__OPENING__TAG__").\
            replace(u"</tx>", u"__TX__CLOSING__TAG__").\
            replace(u"&", "&amp;").\
            replace(u"<", "&lt;").\
            replace(u"__TX__OPENING__TAG__", u"<tx").\
            replace(u"__TX__CLOSING__TAG__", u"</tx>")
