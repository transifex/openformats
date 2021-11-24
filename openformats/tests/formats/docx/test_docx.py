# -*- coding: utf-8 -*-
import unittest

from bs4 import BeautifulSoup

from openformats.formats.docx import DocxFile, DocxHandler
from openformats.strings import OpenString


class DocxTestCase(unittest.TestCase):
    TESTFILE_BASE = 'openformats/tests/formats/docx/files'

    def setUp(self):
        self.handler = DocxHandler()

    def get_content(self, filename):
        path = '{}/{}'.format(self.TESTFILE_BASE, filename)
        with open(path, 'rb') as f:
            content = f.read()
        return content

    def verify_stringset(self, actual_stringset, expected_strings):
        self.assertEqual(len(actual_stringset), len(expected_strings))
        for actual_openstring, expected_string in zip(actual_stringset, expected_strings):
            self.assertEqual(actual_openstring.string, expected_string)

    def prepare_stringset(self, sources, translations_strings):
        self.assertEqual(len(sources), len(translations_strings))
        openstrings = []

        order = 1
        for source, translation in zip(sources, translations_strings):
            openstrings.append(
                OpenString(source.key, translation, order=order)
            )
            order += 1
        return openstrings

    def test_broken_file(self):
        content = self.get_content('missing_wr_parent.docx')
        template, stringset = self.handler.parse(content)
        self.assertEqual(len(stringset), 1)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            u'Foo bar baz'
        )
        self.assertEqual(openstring.string, openstring.key)

        translation = u'Φου βαρ βαζ'
        stringset = [
            OpenString(openstring.key, translation, order=1)
        ]

        content = self.handler.compile(template, stringset)

        template, stringset = self.handler.parse(content)

        self.assertEqual(len(stringset), 1)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            u'Φου βαρ βαζ'
        )

    def test_docx_file(self):
        content = self.get_content('hello_world.docx')

        docx = DocxFile(content)

        for text in [u'Hello world ', u'this is a link']:
            self.assertTrue(text in docx.get_document())

        for url in [u'https://www.transifex.com/']:
            self.assertTrue(url in docx.get_document_rels())

        docx.set_document(u'Modified Document')
        docx.set_document_rels(u'Modified Document Rels')

        content = docx.compress()
        docx.delete()

        docx = DocxFile(content)
        self.assertEqual(docx.get_document(), u'Modified Document')
        self.assertEqual(docx.get_document_rels(), u'Modified Document Rels')

    def test_simple_file(self):
        content = self.get_content('hello_world.docx')
        template, stringset = self.handler.parse(content)

        self.assertEqual(len(stringset), 1)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            u'<tx>Hello world </tx><tx href="https://www.transifex.com/">this is a link</tx>'  # noqa
        )
        self.assertEqual(openstring.string, openstring.key)

        translation = u'<tx>Καλημέρα κόσμε </tx><tx href="https://el.transifex.com/">αυτός είναι ένας κρίκος</tx>'  # noqa
        stringset = [
            OpenString(openstring.key, translation, order=1)
        ]

        content = self.handler.compile(template, stringset)
        template, stringset = self.handler.parse(content)

        self.assertEqual(len(stringset), 1)

        docx = DocxFile(content)

        for text in [u'Hello world ', u'this is a link']:
            self.assertFalse(text in docx.get_document())

        for url in [u'https://www.transifex.com/']:
            self.assertFalse(url in docx.get_document_rels())

        for text in [u'Καλημέρα κόσμε ', u'αυτός είναι ένας κρίκος']:
            self.assertTrue(text in docx.get_document())

        for url in [u'https://el.transifex.com/']:
            self.assertTrue(url in docx.get_document_rels())

        docx.set_document(u'Modified Document')
        docx.set_document_rels(u'Modified Document Rels')

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(openstring.string, translation)
        self.assertEqual(openstring.string, openstring.key)

    def test_space_control(self):
        content = self.get_content('special_cases_2.docx')

        template, stringset = self.handler.parse(content)

        self.assertEqual(len(stringset), 1)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            u'one two <tx href="https://www.transifex.com/">three </tx><tx> four </tx>five'  # noqa
        )
        self.assertEqual(openstring.string, openstring.key)

        translation = u'ενα δύο <tx href="https://www.transifex.com/">τρία </tx><tx> τέσσερα </tx>πέντε'  # noqa
        stringset = [
            OpenString(openstring.key, translation, order=1)
        ]

        content = self.handler.compile(template, stringset)
        template, stringset = self.handler.parse(content)

        self.assertEqual(len(stringset), 1)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            u'ενα δύο <tx href="https://www.transifex.com/">τρία </tx><tx> τέσσερα </tx>πέντε'
        )
        self.assertEqual(openstring.string, openstring.key)

        translation = u'ενα δύο<tx href="https://www.transifex.com/">τρία</tx><tx>τέσσερα</tx>πέντε'  # noqa
        stringset = [
            OpenString(openstring.key, translation, order=1)
        ]

        content = self.handler.compile(template, stringset)
        template, stringset = self.handler.parse(content)

        self.assertEqual(len(stringset), 1)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(
            openstring.string,
            u'ενα δύο<tx href="https://www.transifex.com/">τρία</tx><tx>τέσσερα</tx>πέντε'
        )
        self.assertEqual(openstring.string, openstring.key)

    def test_hyperlink_reorder(self):
        content = self.get_content('special_cases_2.docx')

        template, source_stringset = self.handler.parse(content)
        content = self.handler.compile(template, source_stringset)

        docx = DocxFile(template)
        soup = BeautifulSoup(docx.get_document(), 'xml')
        paragraph = soup.find_all('w:p')[0]
        text_elements_bf_reorder = paragraph.find_all('w:t')
        # reorder href rPr is swapped
        translated_strings = [
            [
                u'ένα δύο ',
                u'<tx>τρία </tx>',
                u'<tx href="https://www.transifex.com/"> τέσσερα </tx>',
                u'πέντε',
            ],
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(source_stringset,
                                          translated_strings):
            translated_stringset.append(
                OpenString(extracted.key, u''.join(translation), order=order)
            )
            order += 1
        content = self.handler.compile(template, translated_stringset)
        _, stringset = self.handler.parse(content)

        docx = DocxFile(content)
        soup = BeautifulSoup(docx.get_document(), 'xml')
        paragraph = soup.find_all('w:p')[0]
        text_elements = paragraph.find_all('w:t')

        self.assertEqual(text_elements[3].parent.rPr.color,
                         text_elements_bf_reorder[1].parent.rPr.color)
        self.assertEqual(text_elements[3].parent.rPr.u,
                         text_elements_bf_reorder[1].parent.rPr.u)
        self.assertEqual(text_elements[1].parent.rPr.color, None)
        self.assertEqual(text_elements[1].parent.rPr.u, None)

    def test_more_extreme_cases(self):
        # Test Original
        content = self.get_content('special_cases_3.docx')
        original_template, original_stringset = self.handler.parse(content)
        self.verify_stringset(
            original_stringset,
            [
                u'Ena <tx>arxeio</tx> me perierges periptwseis',
                u'Kai<tx> ehw kai ena hyperlink </tx><tx href="http://www.google.com/">edw</tx><tx> kai </tx><tx href="http://www.google.gr/">edw</tx>',
                u'Alla edw <tx>exw</tx> ena keno sto telos ',
                u'Kai<tx> edw</tx><tx> den exw </tx><tx>hyperlink</tx> katholou.'
            ]
        )

        # Test spaces at the end and less elements
        translated_stringset = self.prepare_stringset(
            original_stringset,
            [
                u'One <tx>file</tx> with extreme cases',
                u'And<tx> i have a hyperlink </tx><tx href="http://www.google.com/">here</tx><tx> and </tx><tx href="http://www.google.gr/">here</tx> ',
                u'But here <tx>I have </tx> <tx>a space at the end</tx> and more ',
                u'And<tx> here</tx> <tx>I have no </tx><tx>hyperlink</tx> at all.'
            ]
        )

        content = self.handler.compile(original_template, translated_stringset)
        template, stringset = self.handler.parse(content)

        self.verify_stringset(
            stringset,
            [
                u'One <tx>file</tx> with extreme cases',
                u'And<tx> i have a hyperlink </tx><tx href="http://www.google.com/">here</tx><tx> and </tx><tx href="http://www.google.gr/">here </tx>',
                u'But here <tx>I have </tx> a space at the end and more ',
                u'And<tx> here</tx><tx> I have no </tx>hyperlink at all.'
            ]
        )

        # Test swapping with no format
        translated_stringset = self.prepare_stringset(
            stringset,
            [
                u'One <tx>file</tx> with extreme cases',
                u'And<tx href="http://www.google.com/"> hyperlink </tx><tx> was moved </tx> <tx href="http://www.google.gr/">here</tx> <tx>now </tx> ',
                u'But here <tx>I have </tx> <tx>a space at the end</> and more ',
                u'And <tx>here</tx><tx>I have </tx><tx href="www.google.com">hyperlink</tx>'
            ]
        )

        content = self.handler.compile(template, translated_stringset)
        _, stringset = self.handler.parse(content)

        self.verify_stringset(
            stringset,
            [
                u'One <tx>file</tx> with extreme cases',
                u'And<tx href="http://www.google.com/"> hyperlink </tx><tx> was moved </tx><tx href="http://www.google.gr/"> here now  </tx>',
                u'But here <tx>I have </tx> a space at the end</> and more ',
                u'And <tx>here</tx><tx>I have </tx><tx href="www.google.com">hyperlink</tx>'
            ]
        )

    def test_complex_file(self):
        content = self.get_content('complex.docx')
        template, stringset = self.handler.parse(content)

        expected_strings = [
            u'a Title',
            u'a Subtitle',
            u'Heading 1',
            u'Heading 2',
            u'Heading 3',
            u'Internal <tx>styled</tx> link',
            [
                u'This '
                u'<tx>complex text</tx>',
                u'<tx> that</tx>'
                u'<tx> surrounds </tx>'
                u'<tx href="https://www.transifex.com/">a '
                u'<tx>external hyperlink</tx>'
                u'<tx> that </tx>'
                u'<tx>includes a</tx>'
                u'<tx> mix</tx></tx>'
                u'<tx> of </tx>'
                u'<tx>styles </tx>'
                u'<tx>and</tx>'
                u'<tx> it gets</tx>'
                u'<tx> parsed</tx>',
                u' as expected'
            ],
            u'Unordered item 1',
            u'Unordered item 2',
            u'Unordered item 3',
            u'Ordered item 1',
            u'Ordered item 2',
            u'Ordered item 3',
            u'Table 1.1',
            u'Table 1.2',
            u'Table 2.1',
            u'Table 2.2',
            u'↧↨↩'
        ]

        for extracted, expected in zip(stringset, expected_strings):
            self.assertEqual(extracted.string, u''.join(expected))

        docx = DocxFile(template)
        expected_docx_source_text = [
            u'a Title',
            u'a Subtitle',
            u'Heading 1',
            u'Heading 2',
            u'Heading 3',
            u'Internal ',
            u'styled',
            u' link',
            u'This ',
            u'complex text',
            u'that',
            u'surrounds ',
            u'a ',
            u'external hyperlink',
            u' that ',
            u'includes a',
            u' mix',
            u' of ',
            u'styles ',
            u'and',
            u' it gets',
            u'parsed',
            u' as expected',
            u'Unordered item 1',
            u'Unordered item 2',
            u'Unordered item 3',
            u'Ordered item 1',
            u'Ordered item 2',
            u'Ordered item 3',
            u'Table 1.1',
            u'Table 1.2',
            u'Table 2.1',
            u'Table 2.2',
            u'↧↨↩'
        ]
        for text in expected_docx_source_text:
            self.assertTrue(text in docx.get_document())

        for url in [u'https://www.transifex.com/']:
            self.assertTrue(url in docx.get_document_rels())

        translated_strings = [
            u'Τίτλος',
            u'Υπότιτλος',
            u'Επικεφαλίδα 1',
            u'Επικεφαλίδα 2',
            u'Επικεφαλίδα 3',
            u'Eσωτερικός <tx>με στύλ</tx> σύνδεσμος',
            [
                u'Αυτό '
                u'<tx>σύνθετο κείμενο</tx>',
                u'<tx> το οποίο</tx>'
                u'<tx> περιβάλλει </tx>'
                u'<tx href="https://www.el.transifex.com/">έναν '
                u'<tx>σύνδεσμο</tx>'
                u'<tx> που </tx>'
                u'<tx>περιέχει ένα</tx>'
                u'<tx> μείγμα</tx></tx>'
                u'<tx> από </tx>'
                u'<tx>στύλ </tx>'
                u'<tx>και</tx>'
                u'<tx> καταφέρνει να</tx>'
                u'<tx> αναλυθεί</tx>',
                u' όπως αναμένεται'
            ],
            u'Μη ταξινομημένο στοιχείο 1',
            u'Μη ταξινομημένο στοιχείο 2',
            u'Μη ταξινομημένο στοιχείο 3',
            u'Ταξινομημένο στοιχείο 1',
            u'Ταξινομημένο στοιχείο 2',
            u'Ταξινομημένο στοιχείο 3',
            u'Πίνακας 1.1',
            u'Πίνακας 1.2',
            u'Πίνακας 2.1',
            u'Πίνακας 2.2',
            u'Ειδικοί χαρακτήρες'
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(stringset, translated_strings):
            translated_stringset.append(
                OpenString(extracted.key, u''.join(translation), order=order)
            )
            order += 1

        content = self.handler.compile(template, translated_stringset)
        template, stringset = self.handler.parse(content)

        docx = DocxFile(content)

        for extracted, expected in zip(stringset, translated_strings):
            self.assertEqual(extracted.string, u''.join(expected))

        for text in expected_docx_source_text:
            self.assertFalse(text in docx.get_document())

        for url in [u'https://www.transifex.com/']:
            self.assertFalse(url in docx.get_document_rels())

        translated_text = [
            u'Τίτλος',
            u'Υπότιτλος',
            u'Επικεφαλίδα 1',
            u'Επικεφαλίδα 2',
            u'Επικεφαλίδα 3',
            u'Eσωτερικός ',
            u'με στύλ',
            u' σύνδεσμος',
            u'Αυτό ',
            u'σύνθετο κείμενο',
            u'το οποίο',
            u' περιβάλλει ',
            u'έναν ',
            u'σύνδεσμο',
            u' που ',
            u'περιέχει ένα',
            u' μείγμα',
            u' από ',
            u'στύλ ',
            u'και',
            u' καταφέρνει να',
            u'αναλυθεί',
            u' όπως αναμένεται',
            u'Μη ταξινομημένο στοιχείο 1',
            u'Μη ταξινομημένο στοιχείο 2',
            u'Μη ταξινομημένο στοιχείο 3',
            u'Ταξινομημένο στοιχείο 1',
            u'Ταξινομημένο στοιχείο 2',
            u'Ταξινομημένο στοιχείο 3',
            u'Πίνακας 1.1',
            u'Πίνακας 1.2',
            u'Πίνακας 2.1',
            u'Πίνακας 2.2',
            u'Ειδικοί χαρακτήρες'
        ]

        for text in translated_text:
            self.assertTrue(text in docx.get_document())

        for url in [u'https://www.el.transifex.com/']:
            self.assertTrue(url in docx.get_document_rels())

    def test_special_cases_file(self):
        content = self.get_content('special_cases.docx')
        template, source_stringset = self.handler.parse(content)

        expected_strings = [
            [
                u'one two ',
                u'<tx href="https://www.transifex.com/">three ',
                u'<tx>four</tx>',
                u'<tx> five </tx>',
                u'<tx>six</tx>',
                u'<tx> seven eight</tx></tx>',
                u'<tx> nine </tx>',
                u'<tx>ten </tx>',
                u'<tx>eleven</tx>',
                u' twelve'
            ],
        ]

        for extracted, expected in zip(source_stringset, expected_strings):
            self.assertEqual(extracted.string, u''.join(expected))

        docx = DocxFile(template)
        expected_docx_source_text = [
            u'one two',
            u'three ',
            u'four',
            u' five ',
            u'six',
            u' seven eight',
            u' nine ',
            u'ten ',
            u'eleven',
            u' twelve'
        ]
        for text in expected_docx_source_text:
            self.assertTrue(text in docx.get_document())

        for url in [u'https://www.transifex.com/']:
            self.assertTrue(url in docx.get_document_rels())

        # missing href is removed
        translated_strings = [
            [
                u'ένα δύο ',
                u'<tx>τρία </tx>',
                u'<tx>τέσσερα</tx>',
                u'<tx> πέντε </tx>',
                u'<tx>έξι</tx>',
                u'<tx> επτά οχτώ</tx>',
                u'<tx> εννεά </tx>',
                u'<tx>δέκα </tx>',
                u'<tx>έντεκα</tx>',
                u' δώδεκα'
            ],
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(source_stringset,
                                          translated_strings):
            translated_stringset.append(
                OpenString(extracted.key, u''.join(translation), order=order)
            )
            order += 1

        fixed_stringset = [
            [
                u'ένα δύο ',
                u'<tx>τρία </tx>',
                u'<tx>τέσσερα</tx>',
                u'<tx> πέντε </tx>',
                u'<tx>έξι</tx>',
                u'<tx> επτά οχτώ</tx>',
                u'<tx> εννεά </tx>',
                u'<tx>δέκα </tx>',
                u'<tx>έντεκα</tx>',
                u' δώδεκα'
            ],
        ]

        content = self.handler.compile(template, translated_stringset)
        _, stringset = self.handler.parse(content)

        for extracted, expected in zip(stringset, fixed_stringset):
            self.assertEqual(extracted.string, u''.join(expected))

        # reorder href is added
        translated_strings = [
            [
                u'ένα δύο ',
                u'<tx>τρία </tx>',
                u'<tx>τέσσερα</tx>',
                u'<tx> πέντε </tx>',
                u'<tx>έξι</tx>',
                u'<tx> επτά οχτώ</tx>',
                u'<tx> εννεά </tx>',
                u'<tx>δέκα </tx>',
                u'<tx href="https://www.transifex.gr/">έντεκα</tx>',
                u' δώδεκα'
            ],
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(source_stringset,
                                          translated_strings):
            translated_stringset.append(
                OpenString(extracted.key, u''.join(translation), order=order)
            )
            order += 1

        fixed_stringset = [
            [
                u'ένα δύο ',
                u'<tx>τρία </tx>',
                u'<tx>τέσσερα</tx>',
                u'<tx> πέντε </tx>',
                u'<tx>έξι</tx>',
                u'<tx> επτά οχτώ</tx>',
                u'<tx> εννεά </tx>',
                u'<tx>δέκα </tx>',
                u'<tx href="https://www.transifex.gr/">έντεκα</tx>',
                u' δώδεκα'
            ],
        ]

        content = self.handler.compile(template, translated_stringset)
        _, stringset = self.handler.parse(content)

        for extracted, expected in zip(stringset, fixed_stringset):
            self.assertEqual(extracted.string, u''.join(expected))

        docx = DocxFile(content)
        for url in [u'https://www.transifex.gr/']:
            self.assertTrue(url in docx.get_document_rels())

        # missing tags removes elements from docx
        translated_strings = [
            [
                u'ένα δύο ',
                u'<tx>τρία </tx>',
                u'<tx>τέσσερα</tx>',
                u'<tx> πέντε </tx>',
                u'<tx>έξι</tx>',
                u'<tx> επτά οχτώ</tx>',
                u' εννεά ',
                u'δέκα ',
                u'έντεκα',
                u' δώδεκα'
            ],
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(source_stringset,
                                          translated_strings):
            translated_stringset.append(
                OpenString(extracted.key, u''.join(translation), order=order)
            )
            order += 1

        fixed_stringset = [
            [
                u'ένα δύο ',
                u'<tx>τρία </tx>',
                u'<tx>τέσσερα</tx>',
                u'<tx> πέντε </tx>',
                u'<tx>έξι</tx>',
                u'<tx> επτά οχτώ</tx>',
                u' εννεά ',
                u'δέκα ',
                u'έντεκα',
                u' δώδεκα'
            ],
        ]

        content = self.handler.compile(template, translated_stringset)
        _, stringset = self.handler.parse(content)

        for extracted, expected in zip(stringset, fixed_stringset):
            self.assertEqual(extracted.string, u''.join(expected))

        # More tags merge text into last element
        translated_strings = [
            [
                u'ένα δύο ',
                u'<tx href="https://www.transifex.com/">τρία ',
                u'<tx>τέσσερα</tx>',
                u'<tx> πέντε </tx>',
                u'<tx>έξι</tx>',
                u'<tx> επτά οχτώ</tx></tx>',
                u'<tx> εννεά </tx>',
                u'<tx>δέκα </tx>',
                u'<tx>έντεκα</tx>',
                u'<tx> δώδεκα</tx>',
                u'<tx> δεκατρία</tx>',
                u'<tx> δεκατέσσερα</tx>',
                u' δεκαπέντε'
            ],
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(source_stringset,
                                          translated_strings):
            translated_stringset.append(
                OpenString(extracted.key, u''.join(translation), order=order)
            )
            order += 1

        fixed_stringset = [
            [
                u'ένα δύο ',
                u'<tx href="https://www.transifex.com/">τρία ',
                u'<tx>τέσσερα</tx>',
                u'<tx> πέντε </tx>',
                u'<tx>έξι</tx>',
                u'<tx> επτά οχτώ</tx></tx>',
                u'<tx> εννεά </tx>',
                u'<tx>δέκα </tx>',
                u'<tx>έντεκα</tx>',
                u' δώδεκα δεκατρία δεκατέσσερα δεκαπέντε'
            ],
        ]

        content = self.handler.compile(template, translated_stringset)
        _, stringset = self.handler.parse(content)

        for extracted, expected in zip(stringset, fixed_stringset):
            self.assertEqual(extracted.string, u''.join(expected))

    def test_two_text_elements_file(self):
        content = self.get_content('two_text_elements.docx')
        template, source_stringset = self.handler.parse(content)

        expected_strings = [
            u'<tx>Hello</tx><tx> world</tx>',
            u'<tx>Goodbye </tx><tx>world</tx>',
            u'<tx>This is a </tx><tx href="https://google.com/">link</tx>',
            u'<tx>This is my picture </tx><tx> (rest of text goes here).</tx>',
        ]

        for extracted, expected in zip(source_stringset, expected_strings):
            self.assertEqual(extracted.string, u''.join(expected))

        docx = DocxFile(template)
        expected_docx_source_text = [
            u'Hello',
            u' world',
            u'Goodbye ',
            u'world',
            u'This is a ',
            u'link',
            u'This is my picture ',
            u' (rest of text goes here).',
        ]
        for text in expected_docx_source_text:
            self.assertTrue(text in docx.get_document())

        for url in [u'https://google.com/']:
            self.assertTrue(url in docx.get_document_rels())

        translated_strings = [
            u'<tx>Γεία</tx><tx> κόσμε</tx>',
            u'<tx>Αντίο </tx><tx>κόσμε</tx>',
            u'<tx>Αυτό είναι ένα </tx><tx href="https://transifex.com/">λίνκ</tx>',  # noqa
            u'<tx>Και αυτή η εικόνα μου </tx><tx> (υπόλοιπο κείμενο).</tx>',
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(source_stringset,
                                          translated_strings):
            translated_stringset.append(
                OpenString(extracted.key, u''.join(translation), order=order)
            )
            order += 1

        fixed_stringset = [
            u'<tx>Γεία</tx><tx> κόσμε</tx>',
            u'<tx>Αντίο </tx><tx>κόσμε</tx>',
            u'<tx>Αυτό είναι ένα </tx><tx href="https://transifex.com/">λίνκ</tx>',  # noqa
            u'<tx>Και αυτή η εικόνα μου </tx><tx> (υπόλοιπο κείμενο).</tx>',
        ]

        content = self.handler.compile(template, translated_stringset)
        template, stringset = self.handler.parse(content)

        for extracted, expected in zip(stringset, fixed_stringset):
            self.assertEqual(extracted.string, u''.join(expected))

        docx = DocxFile(template)
        expected_docx_source_text = [
            u'Γεία',
            u' κόσμε',
            u'Αντίο ',
            u'κόσμε',
            u'Αυτό είναι ένα ',
            u'λίνκ',
            u'Και αυτή η εικόνα μου ',
            u' (υπόλοιπο κείμενο).',
        ]
        for text in expected_docx_source_text:
            self.assertTrue(text in docx.get_document())

        for url in [u'https://transifex.com/']:
            self.assertTrue(url in docx.get_document_rels())

    def test_ampersand(self):
        content = self.get_content('with_ampersand.docx')
        template, stringset = self.handler.parse(content)

        # Make sure extracted data is OK
        self.assertEqual(len(stringset), 1)
        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(openstring.string,
                         u'This is an & ampersand')
        self.assertEqual(openstring.string, openstring.key)

        # Compile with altered translation
        translation = U'THIS IS AN & AMPERSAND'
        stringset = [
            OpenString(openstring.key, translation, order=0)
        ]
        content = self.handler.compile(template, stringset)

        # Make sure compiled file has altered data
        docx = DocxFile(content)
        self.assertFalse("This is an" in docx.get_document())
        self.assertFalse("ampersand" in docx.get_document())
        self.assertTrue("THIS IS AN" in docx.get_document())
        self.assertTrue("AMPERSAND" in docx.get_document())

        # Parse compiled file
        template, stringset = self.handler.parse(content)

        # Make sure compiled file has the correct translation
        self.assertEqual(len(stringset), 1)
        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(openstring.string, translation)
        self.assertEqual(openstring.string, openstring.key)

    def test_escape_xml(self):
        for original, escaped in (("ab", "ab"),
                                  ("a<b", "a&lt;b"),
                                  ("a<tx>b", "a<tx>b"),
                                  ("a<tx>b<c</tx>", "a<tx>b&lt;c</tx>")):
            self.assertEqual(DocxHandler._escape_xml(original), escaped)

    def test_lt(self):
        # Parse original file
        content = self.get_content('with_lt.docx')
        template, stringset = self.handler.parse(content)

        # Make sure extracted data is OK
        self.assertEqual(len(stringset), 1)
        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(openstring.string,
                         u'This is a < lessthan')
        self.assertEqual(openstring.string, openstring.key)

        # Compile with altered translation
        translation = U'THIS IS A < LESSTHAN'
        stringset = [
            OpenString(openstring.key, translation, order=0)
        ]
        content = self.handler.compile(template, stringset)

        # Make sure compiled file has altered data
        docx = DocxFile(content)
        self.assertFalse("This is a" in docx.get_document())
        self.assertFalse("lessthan" in docx.get_document())
        self.assertTrue("THIS IS A" in docx.get_document())
        self.assertTrue("LESSTHAN" in docx.get_document())

        # Parse compiled file
        template, stringset = self.handler.parse(content)

        # Make sure compiled file has the correct translation
        self.assertEqual(len(stringset), 1)
        openstring = stringset[0]
        self.assertEqual(openstring.order, 0)
        self.assertEqual(openstring.string, translation)
        self.assertEqual(openstring.string, openstring.key)

    def test_rtl(self):
        path = '{}/hello_world.docx'.format(self.TESTFILE_BASE)
        with open(path, 'rb') as f:
            content = f.read()
        handler = DocxHandler()
        template, stringset = handler.parse(content)
        openstring = stringset[0]

        # Compile with altered translation
        translation = u'<tx>Καλημέρα κόσμε </tx><tx href="https://el.transifex.com/">αυτός είναι ένας κρίκος</tx>'  # noqa
        stringset = [
            OpenString(openstring.key, translation, order=1)
        ]

        content = handler.compile(template, stringset, is_rtl=True)
        docx = DocxFile(content)
        soup = BeautifulSoup(docx.get_document(), 'xml')
        self.assertEqual(len(stringset), 1)
        self.assertEqual(len(soup.find_all("w:bidi")), 1)
        for pPr in soup.find_all("w:pPr"):
            self.assertEqual(len(pPr.findChildren("w:bidi")), 1)
            for bidi in pPr.findChildren("w:bidi"):
                self.assertEqual(bidi["w:val"], "1")

        self.assertTrue(len(soup.find_all("w:rtl")), 1)
        for rPr in soup.find_all("w:rPr"):
            self.assertEqual(len(rPr.findChildren("w:rtl")), 1)
            for rtl in rPr.findChildren("w:rtl"):
                self.assertEqual(rtl["w:val"], "1")
