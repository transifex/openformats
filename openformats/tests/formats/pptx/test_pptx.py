# -*- coding: utf-8 -*-
import unittest
import re
import six

from bs4 import BeautifulSoup

from openformats.formats.pptx import PptxFile, PptxHandler
from openformats.strings import OpenString


class PptxTestCase(unittest.TestCase):
    TESTFILE_BASE = 'openformats/tests/formats/pptx/files'

    def test_pptx_file(self):
        path = '{}/hello_world.pptx'.format(self.TESTFILE_BASE)
        with open(path, 'rb') as f:
            content = f.read()

        pptx = PptxFile(content)

        self.assertTrue(u'/ppt/slides/slide1.xml' in pptx.get_slides())
        slide = u'/ppt/slides/slide1.xml'
        for text in [u'Hello World', u'This is a link']:
            self.assertTrue(text in pptx.get_slide(slide))

        for url in [u'http://www.transifex.com']:
            self.assertTrue(url in pptx.get_slide_rels(slide))

        pptx.set_slide(slide, u'Modified slide')
        pptx.set_slide_rels(slide, u'Modified slide Rels')

        content = pptx.compress()
        pptx.delete()

        pptx = PptxFile(content)
        self.assertEqual(u'Modified slide', pptx.get_slide(slide))
        self.assertEqual(
            u'Modified slide Rels', pptx.get_slide_rels(slide)
        )

    def test_file_ordering(self):
        path = '{}/multi.pptx'.format(self.TESTFILE_BASE)
        with open(path, 'rb') as f:
            content = f.read()

        pptx = PptxFile(content)
        self.assertListEqual([
            u'/ppt/slides/slide1.xml',
            u'/ppt/notesSlides/notesSlide1.xml',
            u'/ppt/slides/slide2.xml',
            u'/ppt/notesSlides/notesSlide2.xml',
            u'/ppt/slides/slide3.xml',
            u'/ppt/notesSlides/notesSlide3.xml',
            u'/ppt/slides/slide4.xml',
            u'/ppt/notesSlides/notesSlide4.xml',
            u'/ppt/slides/slide5.xml',
            u'/ppt/notesSlides/notesSlide5.xml',
            u'/ppt/slides/slide6.xml',
            u'/ppt/notesSlides/notesSlide6.xml',
            u'/ppt/slides/slide7.xml',
            u'/ppt/notesSlides/notesSlide7.xml',
            u'/ppt/slides/slide8.xml',
            u'/ppt/notesSlides/notesSlide8.xml',
            u'/ppt/slides/slide9.xml',
            u'/ppt/notesSlides/notesSlide9.xml',
            u'/ppt/slides/slide10.xml',
            u'/ppt/notesSlides/notesSlide10.xml',
            u'/ppt/slides/slide11.xml',
            u'/ppt/notesSlides/notesSlide11.xml'
        ], pptx.get_slides())

    def test_pptx_simple_parser(self):
        path = '{}/hello_world.pptx'.format(self.TESTFILE_BASE)
        with open(path, 'rb') as f:
            content = f.read()

        handler = PptxHandler()
        template, stringset = handler.parse(content)

        self.assertEqual(len(stringset), 2)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            u'Hello World'
        )
        self.assertEqual(openstring.string, openstring.key)
        self.assertIsNone(openstring.tags)

        openstring = stringset[1]
        self.assertEqual(openstring.order, 1)
        self.assertEqual(
            openstring.string,
            u'<tx href="http://www.transifex.com">This is a link</tx>'
        )
        self.assertEqual(openstring.string, openstring.key)
        self.assertIsNone(openstring.tags)

        translated_strings = [
            u'Καλημέρα κόσμε',
            u'<tx href="https://el.transifex.com/">αυτός είναι ένας κρίκος</tx>',
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(stringset, translated_strings):
            translated_stringset.append(
                OpenString(extracted.key, u''.join(translation), order=order)
            )
            order += 1

        content = handler.compile(template, translated_stringset)
        template, stringset = handler.parse(content)

        self.assertEqual(len(stringset), 2)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            u'Καλημέρα κόσμε'
        )
        self.assertEqual(openstring.string, openstring.key)

        openstring = stringset[1]
        self.assertEqual(openstring.order, 1)
        self.assertEqual(
            openstring.string,
            u'<tx href="https://el.transifex.com/">αυτός είναι ένας κρίκος</tx>'
        )
        self.assertEqual(openstring.string, openstring.key)

        pptx = PptxFile(content)

        self.assertTrue(u'/ppt/slides/slide1.xml' in pptx.get_slides())
        slide = u'/ppt/slides/slide1.xml'
        for text in [u'Καλημέρα κόσμε', u'αυτός είναι ένας κρίκος']:
            self.assertTrue(text in pptx.get_slide(slide))

        for url in [u'https://el.transifex.com/']:
            self.assertTrue(url in pptx.get_slide_rels(slide))

    def test_pptx_with_special_characters_parser(self):
        path = '{}/hello_world.pptx'.format(self.TESTFILE_BASE)
        with open(path, 'rb') as f:
            content = f.read()

        handler = PptxHandler()
        template, stringset = handler.parse(content)

        self.assertEqual(len(stringset), 2)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            u'Hello World'
        )
        self.assertEqual(openstring.string, openstring.key)

        openstring = stringset[1]
        self.assertEqual(openstring.order, 1)
        self.assertEqual(
            openstring.string,
            u'<tx href="http://www.transifex.com">This is a link</tx>'
        )
        self.assertEqual(openstring.string, openstring.key)

        translated_strings = [
            u'Καλημέρα & κόσμε',
            u'<tx href="https://el.transifex.com/">αυτός είναι < ένας κρίκος</tx>',
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(stringset, translated_strings):
            translated_stringset.append(
                OpenString(extracted.key, u''.join(translation), order=order)
            )
            order += 1

        content = handler.compile(template, translated_stringset)
        template, stringset = handler.parse(content)

        self.assertEqual(len(stringset), 2)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            u'Καλημέρα & κόσμε'
        )
        self.assertEqual(openstring.string, openstring.key)

        openstring = stringset[1]
        self.assertEqual(openstring.order, 1)
        self.assertEqual(
            openstring.string,
            u'<tx href="https://el.transifex.com/">αυτός είναι < ένας κρίκος</tx>'
        )
        self.assertEqual(openstring.string, openstring.key)

        pptx = PptxFile(content)

        self.assertTrue(u'/ppt/slides/slide1.xml' in pptx.get_slides())
        slide = u'/ppt/slides/slide1.xml'
        for text in [u'Καλημέρα &amp; κόσμε', u'αυτός είναι &lt; ένας κρίκος']:
            self.assertTrue(text in pptx.get_slide(slide))

        for url in [u'https://el.transifex.com/']:
            self.assertTrue(url in pptx.get_slide_rels(slide))

    def test_hyperlinks_reordering(self):
        path = '{}/complex.pptx'.format(self.TESTFILE_BASE)
        with open(path, 'rb') as f:
            content = f.read()

        handler = PptxHandler()
        template, stringset = handler.parse(content)

        self.assertEqual(len(stringset), 2)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            ''.join([
                u'This is a text ',
                u'<tx>with</tx>',
                u'<tx> mixed </tx>',
                u'<tx href="http://www.transifex.com">format</tx>',
                u' and hyperlink'
            ])
        )
        self.assertEqual(openstring.string, openstring.key)

        openstring = stringset[1]
        self.assertEqual(openstring.order, 1)
        self.assertEqual(
            openstring.string,
            ''.join([
                u'Another',
                u'<tx> text </tx>',
                u'<tx>with</tx>',
                u'<tx> mixed </tx>',
                u'<tx href="http://www.transifex.com">format<tx> and</tx></tx>',
                u' hyperlink'
            ])
        )
        self.assertEqual(openstring.string, openstring.key)

        pptx = PptxFile(content)
        slide = u'/ppt/slides/slide1.xml'
        soup = BeautifulSoup(pptx.get_slide(slide), 'xml')
        paragraph_one = soup.find_all('p:sp')[0]
        text_elements_one_before = paragraph_one.find_all('a:t')

        paragraph_two = soup.find_all('p:sp')[1]
        text_elements_two_before = paragraph_two.find_all('a:t')

        translated_strings = [
            [
                u'This is a text ',
                u'<tx href="http://foo.transifex.com">with</tx>',
                u'<tx> mixed </tx>',
                u'<tx>format</tx>',
                u' and hyperlink'
            ],
            [
                u'<tx href="http://bar.transifex.com">Another',
                u'<tx> text </tx>',
                u'<tx>with</tx></tx>',
                u'<tx> mixed </tx>',
                u'<tx>format</tx><tx> and</tx>',
                u' hyperlink'
            ]
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(stringset, translated_strings):
            translated_stringset.append(
                OpenString(extracted.key, u''.join(translation), order=order)
            )
            order += 1

        content = handler.compile(template, translated_stringset)
        template, stringset = handler.parse(content)

        self.assertEqual(len(stringset), 2)
        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            ''.join([
                u'This is a text ',
                u'<tx href="http://foo.transifex.com">with</tx>',
                u'<tx> mixed </tx>',
                u'<tx>format</tx>',
                u' and hyperlink'
            ])
        )
        self.assertEqual(openstring.string, openstring.key)

        openstring = stringset[1]
        self.assertEqual(openstring.order, 1)
        self.assertEqual(
            openstring.string,
            ''.join([
                u'<tx href="http://bar.transifex.com">Another',
                u'<tx> text </tx>',
                u'<tx>with</tx></tx>',
                u'<tx> mixed </tx>',
                u'<tx>format</tx><tx> and</tx>',
                u' hyperlink'
            ])
        )
        self.assertEqual(openstring.string, openstring.key)

        pptx = PptxFile(content)
        slide = u'/ppt/slides/slide1.xml'
        soup = BeautifulSoup(pptx.get_slide(slide), 'xml')
        paragraph = soup.find_all('p:sp')[0]
        text_elements = paragraph.find_all('a:t')

        self.assertEqual(text_elements[3].parent.rPr, text_elements_one_before[1].parent.rPr)
        self.assertEqual(text_elements[1].parent.rPr, text_elements_one_before[3].parent.rPr)

        paragraph = soup.find_all('p:sp')[1]
        text_elements = paragraph.find_all('a:t')

        self.assertEqual(text_elements[0].parent.rPr, text_elements_two_before[4].parent.rPr)
        self.assertEqual(
            re.sub(r'rId\w+', 'rId', six.text_type(text_elements[0].parent.rPr)),
            re.sub(r'rId\w+', 'rId', six.text_type(text_elements_two_before[4].parent.rPr))
        )
        self.assertEqual(
            re.sub(r'rId\w+', 'rId', six.text_type(text_elements[1].parent.rPr)),
            re.sub(r'rId\w+', 'rId', six.text_type(text_elements_two_before[6].parent.rPr))
        )
        self.assertEqual(
            re.sub(r'rId\w+', 'rId', six.text_type(text_elements[2].parent.rPr)),
            re.sub(r'rId\w+', 'rId', six.text_type(text_elements_two_before[6].parent.rPr))
        )

    def test_tags_not_matching(self):
        path = '{}/complex.pptx'.format(self.TESTFILE_BASE)
        with open(path, 'rb') as f:
            content = f.read()

        handler = PptxHandler()
        template, stringset = handler.parse(content)

        self.assertEqual(len(stringset), 2)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            ''.join([
                u'This is a text ',
                u'<tx>with</tx>',
                u'<tx> mixed </tx>',
                u'<tx href="http://www.transifex.com">format</tx>',
                u' and hyperlink'
            ])
        )
        self.assertEqual(openstring.string, openstring.key)

        openstring = stringset[1]
        self.assertEqual(openstring.order, 1)
        self.assertEqual(
            openstring.string,
            ''.join([
                u'Another',
                u'<tx> text </tx>',
                u'<tx>with</tx>',
                u'<tx> mixed </tx>',
                u'<tx href="http://www.transifex.com">format<tx> and</tx></tx>',
                u' hyperlink'
            ])
        )
        self.assertEqual(openstring.string, openstring.key)

        translated_strings = [
            [
                u'This is a text ',
                u'<tx>with</tx>',
                u'<tx> mixed </tx>',
                u'<tx href="http://www.transifex.com">format</tx>',
                u' <tx>and hyperlink</tx> with extra tags'
            ],
            [
                u'Another text with',
                u'<tx> mixed </tx>',
                u'<tx href="http://www.transifex.com">format </tx>',
            ]
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(stringset, translated_strings):
            translated_stringset.append(
                OpenString(extracted.key, u''.join(translation), order=order)
            )
            order += 1

        content = handler.compile(template, translated_stringset)
        template, stringset = handler.parse(content)

        self.assertEqual(len(stringset), 2)
        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            ''.join([
                u'This is a text ',
                u'<tx>with</tx>',
                u'<tx> mixed </tx>',
                u'<tx href="http://www.transifex.com">format</tx>',
                u' and hyperlink with extra tags'
            ])
        )
        self.assertEqual(openstring.string, openstring.key)

        openstring = stringset[1]
        self.assertEqual(openstring.order, 1)
        self.assertEqual(
            openstring.string,
            ''.join([
                u'Another text with',
                u'<tx> mixed </tx>',
                u'<tx href="http://www.transifex.com">format </tx>',
            ])
        )
        self.assertEqual(openstring.string, openstring.key)

    def test_hyperlink_removal(self):
        path = '{}/hello_world.pptx'.format(self.TESTFILE_BASE)
        with open(path, 'rb') as f:
            content = f.read()

        handler = PptxHandler()
        template, stringset = handler.parse(content)

        self.assertEqual(len(stringset), 2)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            u'Hello World'
        )
        self.assertEqual(openstring.string, openstring.key)

        openstring = stringset[1]
        self.assertEqual(openstring.order, 1)
        self.assertEqual(
            openstring.string,
            u'<tx href="http://www.transifex.com">This is a link</tx>'
        )
        self.assertEqual(openstring.string, openstring.key)

        translated_strings = [
            u'Καλημέρα κόσμε',
            u'αυτός είναι ένας κρίκος',
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(stringset, translated_strings):
            translated_stringset.append(
                OpenString(extracted.key, u''.join(translation), order=order)
            )
            order += 1

        content = handler.compile(template, translated_stringset)
        template, stringset = handler.parse(content)

        self.assertEqual(len(stringset), 2)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            u'Καλημέρα κόσμε'
        )
        self.assertEqual(openstring.string, openstring.key)

        openstring = stringset[1]
        self.assertEqual(openstring.order, 1)
        self.assertEqual(
            openstring.string,
            u'αυτός είναι ένας κρίκος'
        )
        self.assertEqual(openstring.string, openstring.key)

    def test_slide_notes(self):
        path = '{}/notes.pptx'.format(self.TESTFILE_BASE)
        with open(path, 'rb') as f:
            content = f.read()

        handler = PptxHandler()
        template, stringset = handler.parse(content)

        self.assertEqual(len(stringset), 1)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            ''.join([
                u'This<tx> slide has only notes and </tx>',
                u'<tx href="http://www.transifex.com">hyperlinks</tx>'
                u'<tx>.</tx>',
                u'<tx>Another </tx>',
                u'<tx>sentence</tx> below'
            ])
        )
        self.assertEqual(openstring.tags, ['notes'])

        translated_strings = [
            [
                u'Αυτό<tx> το slide έχει μόνο notes και </tx>',
                u'<tx href="http://el.transifex.com">συνδέσμους</tx>'
                u'<tx>.</tx>',
                u'<tx>Άλλη μια </tx>',
                u'<tx>πρόταση</tx> από κάτω'
            ]
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(stringset, translated_strings):
            translated_stringset.append(
                OpenString(extracted.key, u''.join(translation), order=order)
            )
            order += 1

        content = handler.compile(template, translated_stringset)
        template, stringset = handler.parse(content)

        self.assertEqual(len(stringset), 1)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            ''.join([
                u'Αυτό<tx> το slide έχει μόνο notes και </tx>',
                u'<tx href="http://el.transifex.com">συνδέσμους</tx>'
                u'<tx>.</tx>',
                u'<tx>Άλλη μια </tx>',
                u'<tx>πρόταση</tx> από κάτω'
            ])
        )
