import six
from copy import deepcopy

from openformats.strings import OpenString
from bs4 import BeautifulSoup
from collections import defaultdict


class OfficeOpenXmlHandler(object):
    @classmethod
    def get_hyperlink_url(cls, element, document_rels):
        raise NotImplementedError

    @classmethod
    def set_hyperlink_url(cls, element, document_rels, url):
        raise NotImplementedError

    @classmethod
    def create_hyperlink_url(cls, element, document_rels, url):
        raise NotImplementedError

    @classmethod
    def remove_hyperlink(cls, text_element):
        raise NotImplementedError

    @classmethod
    def remove_text_element(cls, text_element):
        raise NotImplementedError

    @classmethod
    def swap_hyperlink_elements(
        cls, added_hl_text_elements, deleted_hl_text_elements
    ):
        for added_url, deleted_url in zip(
            added_hl_text_elements.keys(),
            deleted_hl_text_elements.keys()
        ):
            replacements = {}
            for index, e in enumerate(added_hl_text_elements[added_url]):
                if 0 <= index < len(deleted_hl_text_elements[deleted_url]):
                    deleted_format = deleted_hl_text_elements[deleted_url][index].parent.rPr
                else:
                    deleted_format = deleted_hl_text_elements[deleted_url][-1].parent.rPr
                deleted_format = deepcopy(deleted_format)
                replacements[e] = deleted_format
            for index, e in enumerate(deleted_hl_text_elements[deleted_url]):
                if 0 <= index < len(added_hl_text_elements[added_url]):
                    added_format = added_hl_text_elements[added_url][index].parent.rPr
                else:
                    added_format = added_hl_text_elements[added_url][-1].parent.rPr
                added_format = deepcopy(added_format)
                replacements[e] = added_format
            
            for text_element, format in six.iteritems(replacements):
                text_element.parent.rPr.replaceWith(format)

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

    @classmethod
    def parse_paragraph(cls, paragraph, rels_soup):
        paragraph_text = []
        text_elements = paragraph.find_all(cls.TEXT_ELEMENT_TAG)
        if not text_elements:
            return None

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

            hyperlink_url = cls.get_hyperlink_url(
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
            return None

        open_string = OpenString(
            paragraph_text,
            paragraph_text,
        )
        paragraph.attrs['txid'] = open_string.string_hash
        
        return open_string

    def compile_paragraph(cls, paragraph, rels_soup, stringset):
        text_elements = paragraph.find_all(cls.TEXT_ELEMENT_TAG)
        if not text_elements:
            return

        txid = paragraph.attrs.get('txid')

        if not txid:
            return

        if stringset.get(txid, None) is None:
            return

        translation = stringset[txid].string
        translation = cls._escape_xml(translation)

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
                hyperlink_url = cls.get_hyperlink_url(
                    text_element, rels_soup
                )
                # the text parts of the translation are less that the
                # text parts of the document, so we will just remove
                # any excessing part from the document
                if len(translation_soup) == 0:
                    cls.remove_text_element(text_element)
                    continue
                translation_part = translation_soup.pop(0)
                translation = six.text_type(translation_part)
                if not translation[:leading_spaces].strip():
                    translation = translation[leading_spaces:]
                leading_spaces = 0

            # the text parts of the translation are more that the
            # text parts of the document, so we will compress the
            # remaining translation parts into one string
            if (index == len(text_elements) - 1 and len(translation_soup) > 0):
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
                cls.set_hyperlink_url(
                    text_element, rels_soup, translation_hyperlink_url
                )

            # remove hyperlink from source docx
            if hyperlink_url and not translation_hyperlink_url:
                deleted_hl_text_elements[hyperlink_url].append(text_element)

            # create a new hyperlink
            if not hyperlink_url and translation_hyperlink_url:
                added_hl_text_elements[translation_hyperlink_url].append(
                    text_element
                )

            text_element.clear()
            text_element.insert(0, translation)


        if len(added_hl_text_elements) == len(deleted_hl_text_elements):
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
