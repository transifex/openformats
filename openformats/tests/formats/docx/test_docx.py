# -*- coding: utf-8 -*-
import unittest
import io
from openformats.formats.docx import DocxHandler, DocxFile
from openformats.strings import OpenString


class DocxTestCase(unittest.TestCase):
    TESTFILE_BASE = 'openformats/tests/formats/docx/files'

    def test_docx_file(self):   
        path = '{}/hello_world.docx'.format(self.TESTFILE_BASE)
        with open(path, 'rb') as f:
            content = f.read()

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
        path = '{}/hello_world.docx'.format(self.TESTFILE_BASE)
        with open(path, 'rb') as f:
            content = f.read()

        handler = DocxHandler()
        template, stringset = handler.parse(content)

        self.assertEqual(len(stringset), 1)

        openstring = stringset[0]
        self.assertEqual(openstring.order, 1)
        self.assertEqual(
            openstring.string,
            u'Hello world <tx href="https://www.transifex.com/">this is a link</tx>'
        )
        self.assertEqual(openstring.string, openstring.key)

        translation = u'Καλημέρα κόσμε <tx href="https://el.transifex.com/">αυτός είναι ένας κρίκος</tx>'
        stringset = [
            OpenString(openstring.key, translation,order=1)
        ]

        content = handler.compile(template, stringset)
        template, stringset = handler.parse(content)

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
        self.assertEqual(openstring.order, 1)
        self.assertEqual(openstring.string, translation)
        self.assertEqual(openstring.string, openstring.key)

    def test_complex_file(self):
        path = '{}/complex.docx'.format(self.TESTFILE_BASE)
        with open(path, 'rb') as f:
            content = f.read()

        handler = DocxHandler()
        template, stringset = handler.parse(content)

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

        content = handler.compile(template, translated_stringset)
        template, stringset = handler.parse(content)

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
        path = '{}/special_cases.docx'.format(self.TESTFILE_BASE)
        with open(path, 'rb') as f:
            content = f.read()

        handler = DocxHandler()
        template, source_stringset = handler.parse(content)
        content = handler.compile(template, source_stringset)

        docx = DocxFile(content)

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

        # missing href is kept as original
        translated_strings = [
            [
                u'ένα δύο ',
                u'<tx>τρία ',
                u'<tx>τέσσερα</tx>',
                u'<tx> πέντε </tx>',
                u'<tx>έξι</tx>',
                u'<tx> επτά οχτώ</tx></tx>',
                u'<tx> εννεά </tx>',
                u'<tx>δέκα </tx>',
                u'<tx>έντεκα</tx>',
                u' δώδεκα'
            ],
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(source_stringset, translated_strings):
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
                u' δώδεκα'
            ],
        ]

        content = handler.compile(template, translated_stringset)
        _, stringset = handler.parse(content)

        for extracted, expected in zip(stringset, fixed_stringset):
            self.assertEqual(extracted.string, u''.join(expected))

        # missing tags removes elements from docx
        translated_strings = [
            [
                u'ένα δύο ',
                u'<tx>τρία ',
                u'<tx>τέσσερα</tx>',
                u'<tx> πέντε </tx>',
                u'<tx>έξι</tx>',
                u'<tx> επτά οχτώ</tx></tx>',
                u' εννεά ',
                u'δέκα ',
                u'έντεκα',
                u' δώδεκα'
            ],
        ]

        translated_stringset = []
        order = 1
        for extracted, translation in zip(source_stringset, translated_strings):
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
                u' εννεά ',
                u'δέκα ',
                u'έντεκα',
                u' δώδεκα'
            ],
        ]

        content = handler.compile(template, translated_stringset)
        _, stringset = handler.parse(content)

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
        for extracted, translation in zip(source_stringset  , translated_strings):
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

        content = handler.compile(template, translated_stringset)
        _, stringset = handler.parse(content)

        for extracted, expected in zip(stringset, fixed_stringset):
            self.assertEqual(extracted.string, u''.join(expected))
