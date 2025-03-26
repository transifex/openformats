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
from openformats.exceptions import MissingParentError
from openformats.formats.office_open_xml.parser import OfficeOpenXmlHandler
from openformats.strings import OpenString
from collections import defaultdict


class PptxFile(object):
    """
    A class used to wrap and expose the internals of a .xlsx file

    A pptx file is a zipped file that when unzipped,
    generates a similar file/folder structure:
        /ppt/
            /slide{index}.xml
            /_rels/
                /slide{index}.xml.rels
            ...

    The parts that are in interesting are:
        * slide{index}.xml: that contains all(*) the textual content
          that exists in the a single slide
        * _rels/slide{index}.xml.rels slides's relationships, follows the rule
          slide{index}.xml links to `{document path}/ppt/slide{index}.xml.rels`

    The structure of a slide file is as following:
    ```
    <p:sld>
        <p:cSld>
            <p:spTree>
                ...
                <p:sp>
                    ...
                    <a:r>
                        ...
                        <a:t>hello</a:t>
                        ...
                    </a:r>
                    ...
                    <a:r>
                        ...
                        <a:t>world</a:t>
                        ...
                    </a:r>
                    ...
                </p:sp>
                ...
                <p:sp>
                    <a:r>
                        <a:rPr>
                            ...
                            <a:hlinkClick r:id="rId6"/>
                            ...
                        </a:rPr>
                        ...
                        <a:t>Hyperlink</a:t>
                        ...
                    </a:r>
                </p:sp>
            </p:spTree>
        </p:cSld>
        ...
    </p:sld>
    ```

    The text is located at `<a:t>` tags.

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

        pptx_path = '{}/{}.pptx'.format(self.__tmp_folder, 'in')
        with io.open(pptx_path, 'wb') as f:
            f.write(content)

        with ZipFile(pptx_path, 'r') as z:
            z.extractall(self.__tmp_folder)

        self.__filelist = z.namelist()

        os.remove(pptx_path)

        content_types_path = '{}/{}'.format(
            self.__tmp_folder, '[Content_Types].xml'
        )
        with io.open(content_types_path, 'r') as f:
            content_types = f.read()

        slide_content_type = 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml'  # noqa
        slide_paths = [
            relationship.attrs['PartName']
            for relationship in BeautifulSoup(
                content_types, 'xml'
            ).find_all(attrs={'ContentType': slide_content_type})
        ]

        notes_content_type = 'application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml'  # noqa
        notes_paths = [
            relationship.attrs['PartName']
            for relationship in BeautifulSoup(
                content_types, 'xml'
            ).find_all(attrs={'ContentType': notes_content_type})
        ]

        self.__slides = {}
        for slide_path in slide_paths:
            self.__slides[slide_path] = {
                'slide': {
                    'content': None,
                    'path': '{}{}'.format(self.__tmp_folder, slide_path),
                    'notes':  False
                },
                'rels': {
                    'content': None,
                    'path': '{}{}'.format(self.__tmp_folder, self.get_rels_path(slide_path))  # noqa
                }
            }

        for notes_path in notes_paths:
            self.__slides[notes_path] = {
                'slide': {
                    'content': None,
                    'path': '{}{}'.format(self.__tmp_folder, notes_path),
                    'notes':  True
                },
                'rels': {
                    'content': None,
                    'path': '{}{}'.format(self.__tmp_folder, self.get_rels_path(notes_path))  # noqa
                }
            }

    def get_rels_path(self, slides_path):
        path = slides_path.split('/')
        path.insert(-1, '_rels')
        path = '/'.join(path)
        path += '.rels'
        return path

    def get_slides(self):
        slides = []
        main_slides = self._get_sorted_main_slides()
        for main_slide in main_slides:
            slides.append(main_slide)
            related_note = self._get_note_slide_if_exists(main_slide)
            if related_note:
                slides.append(related_note)
        return slides

    def get_slide(self, slide):
        if self.__slides[slide]['slide']['content'] is None:
            with io.open(self.__slides[slide]['slide']['path'], 'r') as f:
                self.__slides[slide]['slide']['content'] = f.read()

        return self.__slides[slide]['slide']['content']

    def is_notes_slide(self, slide):
        return self.__slides[slide]['slide']['notes']

    def set_slide(self, slide, content):
        self.__slides[slide]['slide']['content'] = content

        with io.open(self.__slides[slide]['slide']['path'], 'w') as f:
            f.write(content)

    def get_slide_rels(self, slide):
        if self.__slides[slide]['rels']['content'] is None:
            with io.open(self.__slides[slide]['rels']['path'], 'r') as f:
                self.__slides[slide]['rels']['content'] = f.read()

        return self.__slides[slide]['rels']['content']

    def set_slide_rels(self, slide, content):
        self.__slides[slide]['rels']['content'] = content

        with io.open(self.__slides[slide]['rels']['path'], 'w') as f:
            f.write(content)

    def compress(self):
        pptx_path = '{}/{}.pptx'.format(self.__tmp_folder, 'out')

        with ZipFile(pptx_path, "w", compression=ZIP_DEFLATED) as z:
            for filename in self.__filelist:
                z.write(os.path.join(self.__tmp_folder, filename), filename)

        with io.open(pptx_path, 'rb') as f:
            result = f.read()

        os.remove(pptx_path)

        return result

    def delete(self):
        shutil.rmtree(self.__tmp_folder)

    def _get_slide_number(self, slide):
        """Extract the slide number

        :param slide: A representation of a slide
        :type slide: str
        :return: The number of the slide (its ordering inside the file)
        :rtype: int
        """
        return int(re.findall(r"(\d+)", slide)[0])

    def _get_sorted_main_slides(self):
        """Sort .pptx slides based on their numbering

        :return: Sorted list of slides
        :rtype: List[str]
        """
        main_slides = [
            slide
            for slide in six.iterkeys(self.__slides)
            if not self.is_notes_slide(slide)
        ]
        return sorted(main_slides, key=self._get_slide_number)

    def _get_note_slide_if_exists(self, slide):
        """Retrieve note for a given slide

        :param slide: A slide (e.g. `/ppt/slides/slide1.xml`)
        :type slide: str
        :return: The corresponding note (e.g. `/ppt/notesSlides/notesSlide1.xml`)
            or `None`, if not exists
        :rtype: Optinal[str]
        """
        rels_soup = BeautifulSoup(self.get_slide_rels(slide), "xml")
        relationships = rels_soup.find_all("Relationship")
        related_note_number = None
        for relationship in relationships:
            if "relationships/notesSlide" in relationship.get("Type"):
                related_note_number = self._get_slide_number(relationship.get("Target"))
                break
        return (
            "/ppt/notesSlides/notesSlide{}.xml".format(related_note_number)
            if related_note_number
            else None
        )


class PptxHandler(Handler, OfficeOpenXmlHandler):
    PROCESSES_BINARY = True
    EXTRACTS_RAW = False
    name = "PPTX"
    TEXT_ELEMENT_TAG = "a:t"

    @classmethod
    def get_hyperlink_url(cls, element, document_rels):
        parent = element.find_parent('a:r')

        if not parent:
            raise MissingParentError

        hyperlinks = parent.find_all('a:hlinkClick', limit=1)
        if hyperlinks:
            rel = document_rels.find(
                attrs={'Id': hyperlinks[0].attrs.get('r:id')}
            )
            if rel and rel.attrs.get('TargetMode') == 'External':
                return rel.attrs['Target']

        return None

    @classmethod
    def set_hyperlink_url(cls, element, document_rels, url):
        parent = element.find_parent('a:r')

        hyperlinks = parent.find_all('a:hlinkClick', limit=1)
        if hyperlinks:
            rel = document_rels.find(
                attrs={'Id': hyperlinks[0].attrs.get('r:id')}
            )
            if rel and rel.attrs.get('TargetMode') == 'External':
                rel.attrs['Target'] = url

    @classmethod
    def create_hyperlink_url(cls, element, document_rels, url):
        if cls.get_hyperlink_url(element, document_rels):
            cls.set_hyperlink_url(element, document_rels, url)
        else:
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
                "a:hlinkClick",
                **{"r:id": rid}
            )
            element.parent.rPr.append(hyperlink)

    @classmethod
    def remove_hyperlink(cls, text_element):
        parent = text_element.find_parent('a:r')
        hyperlinks = parent.find_all('a:hlinkClick', limit=1)
        if hyperlinks:
            hyperlinks[0].decompose()

    @classmethod
    def remove_text_element(cls, text_element):
        text_element.decompose()

    @classmethod
    def set_rtl_orientation(cls, paragraph):
        ppr_tags = paragraph.find_all("a:pPr")
        for ppr_tag in ppr_tags:
            ppr_tag["rtl"] = "1"
            if ppr_tag.get("algn") == "l":
                ppr_tag["algn"] = "r"

    def parse(self, content, **kwargs):
        """
        We will segment the text by paragraph `<w:p>` as this
        is defined in the pptx structure.

        For all the text `<w:t>` inside a paragraph,
        we use tag separators `<tx>`, in order to denote
        text style changes (normal->bold, bold->italic, 10px->14px etc)
        or hyperlinks that are present in the text.

        In each paragraph we will attach the hash of the openstring
        as `txid` attribute in order to be able to match when
        compilation takes place.
        """
        pptx = PptxFile(content)

        stringset = []
        order = itertools.count()

        for slide in pptx.get_slides():
            notes_slide = pptx.is_notes_slide(slide)
            soup = BeautifulSoup(pptx.get_slide(slide), 'xml')
            rels_soup = BeautifulSoup(pptx.get_slide_rels(slide), 'xml')

            for parent in soup.find_all(['p:sp', 'p:graphicFrame']):
                for paragraph in parent.find_all('a:p'):
                    open_string = self.parse_paragraph(paragraph, rels_soup)
                    if not open_string:
                        continue

                    open_string.order = next(order)
                    if notes_slide:
                        open_string.tags = ['notes']
                    stringset.append(open_string)

            pptx.set_slide(slide, six.text_type(soup))

        template = pptx.compress()
        pptx.delete()
        return template, stringset

    def compile(self, template, stringset, **kwargs):
        stringset = {
            string.string_hash: string for string in stringset
        }
        pptx = PptxFile(template)
        is_rtl = kwargs.get('is_rtl', False)
        for slide in pptx.get_slides():
            soup = BeautifulSoup(pptx.get_slide(slide), 'xml')
            rels_soup = BeautifulSoup(pptx.get_slide_rels(slide), 'xml')

            for parent in soup.find_all(['p:sp', 'p:graphicFrame']):
                for paragraph in parent.find_all('a:p'):
                    self.compile_paragraph(
                        paragraph, rels_soup, stringset, is_rtl=is_rtl
                    )

            pptx.set_slide(slide, six.text_type(soup))
            pptx.set_slide_rels(slide, six.text_type(rels_soup))

        result = pptx.compress()
        pptx.delete()
        return result

class PptxHandlerV2(PptxHandler):
    """
    New version of the PptxHandler that handles empty spaces in the text elements as
    normal text, instead of prepending it to the next text element.
    """
    name = "PPTX_V2"
    
    @classmethod
    def parse_paragraph(cls, paragraph, rels_soup):
        paragraph_text = []
        text_elements = paragraph.find_all(cls.TEXT_ELEMENT_TAG)
        if not text_elements:
            return None

        text_elements_count = len(text_elements)

        open_hyperlink = None        
        for index, text_element in enumerate(text_elements):
            text = text_element.text            

            try:
                hyperlink_url = cls.get_hyperlink_url(
                    text_element, rels_soup
                )
            except MissingParentError:
                continue

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
            return None

        open_string = OpenString(
            paragraph_text,
            paragraph_text,
        )
        paragraph.attrs['txid'] = open_string.string_hash

        return open_string

    def compile_paragraph(cls, paragraph, rels_soup, stringset, is_rtl=False):
        text_elements = paragraph.find_all(cls.TEXT_ELEMENT_TAG)
        if not text_elements:
            return

        txid = paragraph.attrs.get('txid')

        if not txid:
            return

        if stringset.get(txid, None) is None:
            return

        translation_string = stringset[txid].string
        escaped_translation_string = cls._escape_xml(translation_string)

        translation_soup = BeautifulSoup(
            u'<wrapper>{}</wrapper>'.format(escaped_translation_string), 'xml',
        ).find_all(text=True)

        added_hl_text_elements = defaultdict(list)
        deleted_hl_text_elements = defaultdict(list)
        elements_for_removal = []
        last_element = None

        # First of all try to replace each element translation
        # this is the happiest path
        if is_rtl:
            cls.set_rtl_orientation(paragraph)

        for _, text_element in enumerate(text_elements):
            last_element = text_element
            try:
                hyperlink_url = cls.get_hyperlink_url(text_element, rels_soup)
            except MissingParentError:
                continue

            # the text parts of the translation are less that the
            # text parts of the document, so we will just remove
            # any exceeding part from the document
            if len(translation_soup) == 0:
                elements_for_removal.append(text_element)
                continue
            else:
                translation_part = translation_soup.pop(0)
                translation = six.text_type(translation_part)
                translation_hyperlink_url = cls.get_translation_hyperlink(translation_part)

                text_element.clear()
                text_element.insert(0, translation)

            # Edit in place hyperlink url
            if hyperlink_url and translation_hyperlink_url:
                cls.set_hyperlink_url(
                    text_element, rels_soup, translation_hyperlink_url
                )
            else:
                if hyperlink_url:
                    deleted_hl_text_elements[hyperlink_url]\
                        .append(text_element)
                elif translation_hyperlink_url:
                    added_hl_text_elements[translation_hyperlink_url]\
                        .append(text_element)

        # the text parts of the translation are more that the
        # text parts of the document, so we will compress the
        # remaining translation parts into one string
        if len(translation_soup) > 0 and last_element and last_element.contents:
            translation = last_element.contents[0] + \
                          "".join([six.text_type(t) for t in translation_soup]
            )
            last_element.clear()
            last_element.insert(0, translation)

        if len(added_hl_text_elements) == len(deleted_hl_text_elements)\
                and len(added_hl_text_elements) > 0:
            cls.swap_hyperlink_elements(
                added_hl_text_elements,
                deleted_hl_text_elements
            )

        for text_elements in six.itervalues(deleted_hl_text_elements):
            for text_element in text_elements:
                cls.remove_hyperlink(text_element)

        for url, text_elements in six.iteritems(added_hl_text_elements):
            for text_element in text_elements:
                cls.create_hyperlink_url(text_element, rels_soup, url)

        for element in elements_for_removal:
            cls.remove_text_element(element)