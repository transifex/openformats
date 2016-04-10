import re
import unittest

from openformats.utils.xml import NewDumbXml


class DumbXmlTestCase(unittest.TestCase):
    def test_no_embeds(self):
        cases = (
            # Without content
            ('<a/>', 0, 'a', {}, None, None, 4, '', 4),
            ('<a:b/>', 0, 'a:b', {}, None, None, 6, '', 6),
            (' <a/>', 1, 'a', {}, None, None, 5, '', 5),
            ('<a />', 0, 'a', {}, None, None, 5, '', 5),
            ('<a/ >', 0, 'a', {}, None, None, 5, '', 5),
            ('<a/> tail', 0, 'a', {}, None, None, 4, ' tail', 9),
            ('<a b="c" d:e="f"/>', 0, 'a', {'b': "c", 'd:e': "f"}, None, None,
             18, '', 18),
            ('<a b="c" d="e" />', 0, 'a', {'b': "c", 'd': "e"}, None, None, 17,
             '', 17),
            ('<a b="c/d" e="f"/>', 0, 'a', {'b': "c/d", 'e': "f"}, None, None,
             18, '', 18),
            ('<a b="c>d" e="f"/>', 0, 'a', {'b': "c>d", 'e': "f"}, None, None,
             18, '', 18),

            # Comments
            ('<!---->', 0, NewDumbXml.COMMENT, {}, 4, '', 7, '', 7),
            ('<!-- hello there -->', 0, NewDumbXml.COMMENT, {}, 4,
             ' hello there ', 20, '', 20),
            ('<!-- hello there --> tail', 0, NewDumbXml.COMMENT, {}, 4,
             ' hello there ', 20, ' tail', 25),

            # With content
            ('<a></a>', 0, 'a', {}, 3, '', 7, '', 7),
            ('<a></a> tail', 0, 'a', {}, 3, '', 7, ' tail', 12),
            ('<a b="c"></a> tail', 0, 'a', {'b': "c"}, 9, '', 13, ' tail', 18),
            ('<a>hello world</a>', 0, 'a', {}, 3, 'hello world', 18, '', 18),
            ('<a>hello <![CDATA[</a>]]></a>', 0, 'a', {}, 3,
             'hello <![CDATA[</a>]]>', 29, '', 29),
            ('<a>hello world</a> tail', 0, 'a', {}, 3, 'hello world', 18,
             ' tail', 23),
            ('<a b="c">hello world</a> tail', 0, 'a', {'b': "c"}, 9,
             'hello world', 24, ' tail', 29),
        )
        for case in cases:
            dumb_xml = NewDumbXml(case[0])
            self.assertEquals(
                (dumb_xml.source, dumb_xml.position, dumb_xml.tag,
                 dumb_xml.attrib, dumb_xml.text_position, dumb_xml.text,
                 dumb_xml.tail_position, dumb_xml.tail, dumb_xml.end),
                case
            )

    def test_no_embeds_errors(self):
        cases = (('<a', "Opening tag not closed"),
                 ('<a b="c"', "Opening tag not closed"),
                 ('<a', "Opening tag not closed"),
                 ('<a/', "Opening tag not closed"),
                 ('<a /', "Opening tag not closed"),
                 ('<a/oiajod', "Opening tag not closed"),
                 ('<a>', "Tag not closed"),
                 ('<a>hello world', "Tag not closed"),
                 ('<!---', "Comment not closed"),
                 ('<!--jafosijdfoas-', "Comment not closed"))
        for source, error_msg in cases:
            with self.assertRaisesRegexp(ValueError, re.escape(error_msg)):
                dumb_xml = NewDumbXml(source)
                dumb_xml.end  # should expand all properties eventually

    def test_one_child(self):
        cases = (
            # Without content
            ('<r><a/></r>', 3, 'a', {}, None, None, 7, '', 7),
            ('<r><a:b/></r>', 3, 'a:b', {}, None, None, 9, '', 9),
            ('<r> <a/></r>', 4, 'a', {}, None, None, 8, '', 8),
            ('<r><a /></r>', 3, 'a', {}, None, None, 8, '', 8),
            ('<r><a/ ></r>', 3, 'a', {}, None, None, 8, '', 8),
            ('<r><a/> tail</r>', 3, 'a', {}, None, None, 7, ' tail', 12),
            ('<r><a b="c" d:e="f"/></r>', 3, 'a', {'b': "c", 'd:e': "f"}, None,
             None, 21, '', 21),
            ('<r><a b="c" d="e" /></r>', 3, 'a', {'b': "c", 'd': "e"}, None,
             None, 20, '', 20),
            ('<r><a b="c/d" e="f"/></r>', 3, 'a', {'b': "c/d", 'e': "f"}, None,
             None, 21, '', 21),
            ('<r><a b="c>d" e="f"/></r>', 3, 'a', {'b': "c>d", 'e': "f"}, None,
             None, 21, '', 21),

            # Comments
            ('<r><!----></r>', 3, NewDumbXml.COMMENT, {}, 7, '', 10, '', 10),
            ('<r><!-- hello there --></r>', 3, NewDumbXml.COMMENT, {}, 7,
             ' hello there ', 23, '', 23),
            ('<r><!-- hello there --> tail</r>', 3, NewDumbXml.COMMENT, {}, 7,
             ' hello there ', 23, ' tail', 28),

            # With content
            ('<r><a></a></r>', 3, 'a', {}, 6, '', 10, '', 10),
            ('<r><a></a> tail</r>', 3, 'a', {}, 6, '', 10, ' tail', 15),
            ('<r><a b="c"></a> tail</r>', 3, 'a', {'b': "c"}, 12, '', 16,
             ' tail', 21),
            ('<r><a>hello world</a></r>', 3, 'a', {}, 6, 'hello world', 21, '',
             21),
            ('<r><a>hello <![CDATA[</a>]]></a></r>', 3, 'a', {}, 6,
             'hello <![CDATA[</a>]]>', 32, '', 32),
            ('<r><a>hello world</a> tail</r>', 3, 'a', {}, 6, 'hello world',
             21, ' tail', 26),
            ('<r><a b="c">hello world</a> tail</r>', 3, 'a', {'b': "c"}, 12,
             'hello world', 27, ' tail', 32),
        )
        for case in cases:
            root = NewDumbXml(case[0])
            children = list(root)
            self.assertEquals(len(children), 1)
            inner = children[0]
            self.assertEquals(
                (inner.source, inner.position, inner.tag, inner.attrib,
                 inner.text_position, inner.text, inner.tail_position,
                 inner.tail, inner.end),
                case
            )

    def test_several_children(self):
        cases = (
            ['<a />'],
            ['<a><b/><c>hello world</c></a >', '<b/>', '<c>hello world</c>'],
            ['<a><b/><c>hello world</c></a>', '<b/>', '<c>hello world</c>'],
            ['<a><b c="d"/><e>hello world</e></a>', '<b c="d"/>',
             '<e>hello world</e>'],
            ['<a><b/><c d="e">hello world</c></a>', '<b/>',
             '<c d="e">hello world</c>'],
            ['<a><b><c /></b></a>', '<b><c /></b>'],
            ['<a><b><c /></b><d /></a>', '<b><c /></b>', '<d />'],
        )
        for case in cases:
            root_source = case[0]
            children_sources = case[1:]
            root = NewDumbXml(root_source)
            self.assertEquals(
                [inner.source[inner.position:inner.end] for inner in root],
                children_sources
            )

    def test_iter_errors(self):
        cases = (
            ('<a></b>', "Closing tag does not match opening tag"),
            ('<a></a', "Invalid closing of tag"),
            ('<a></a aosdjfio', "Invalid closing of tag"),
        )
        for source, error_msg in cases:
            with self.assertRaisesRegexp(ValueError, re.escape(error_msg)):
                list(NewDumbXml(source))

    def test_inbetweens(self):
        root = NewDumbXml('<a>This<b/>is<c/>separated<d/>by<e/>tags</a>')
        collected = [root.text]
        for inner in root:
            collected.append(inner.tail)
        self.assertEquals(collected, ['This', 'is', 'separated', 'by', 'tags'])

    def test_find_children(self):
        root = NewDumbXml("""
            <ul>
                <li>one</li>
                <something_else>something else</something_else>
                <li>two</li>
                <div>
                    <li>This won't be collected</li>
                </div>
                <li highlight="true">three</li>
            </ul>
        """)
        self.assertEquals(
            [(inner.tag, inner.attrib, inner.text)
             for inner in root.find_children('li')],
            [('li', {}, "one"), ('li', {}, "two"),
             ('li', {'highlight': "true"}, "three")]
        )

    def test_find_all_children(self):
        root = NewDumbXml("""
            <ul>
                <li>one</li>
                <something_else>something else</something_else>
                <li>two</li>
                <div>
                    <li>This won't be collected</li>
                </div>
                <li highlight="true">three</li>
            </ul>
        """)
        self.assertEquals(
            [(inner.tag, inner.attrib, inner.text.strip())
             for inner in root.find_children()],
            [('li', {}, "one"),
             ('something_else', {}, "something else"),
             ('li', {}, "two"),
             ('div', {}, ""),
             ('li', {'highlight': "true"}, "three")]
        )

    def test_find_descendants(self):
        root = NewDumbXml("""
            <div>
                <p>Header</p>
                <div>
                    <p class="icon icon-subheader">Subheader</p>
                    <img src="foo" alt="bar" />
                </div>
            </div>
        """)
        self.assertEquals(
            [(inner.tag, inner.attrib, inner.text)
             for inner in root.find_descendants('p')],
            [('p', {}, "Header"),
             ('p', {'class': "icon icon-subheader"}, "Subheader")]
        )

    def test_find_all_descendants(self):
        root = NewDumbXml("""
            <div>
                <p>Header</p>
                <div>
                    <p class="icon icon-subheader">Subheader</p>
                    <img src="foo" alt="bar" />
                </div>
            </div>
        """)
        self.assertEquals(
            [(inner.tag, inner.attrib, inner.text and inner.text.strip())
             for inner in root.find_descendants()],
            [('p', {}, "Header"),
             ('div', {}, ""),
             ('p', {'class': "icon icon-subheader"}, "Subheader"),
             ('img', {'src': "foo", 'alt': "bar"}, None)]
        )
