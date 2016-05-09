import re
import unittest

from openformats.utils.xml import NewDumbXml, DumbXmlSyntaxError


class DumbXmlTestCase(unittest.TestCase):
    def test_no_embeds(self):
        cases = (
            # Without content
            ('<a/>', 0, 'a', {}, None, None, None, None, 4, '', 4),
            ('<a:b/>', 0, 'a:b', {}, None, None, None, None, 6, '', 6),
            (' <a/>', 1, 'a', {}, None, None, None, None, 5, '', 5),
            ('<a />', 0, 'a', {}, None, None, None, None, 5, '', 5),
            ('<a/ >', 0, 'a', {}, None, None, None, None, 5, '', 5),
            ('<a/> tail', 0, 'a', {}, None, None, None, None, 4, ' tail', 9),
            ('<a b="c" d:e="f"/>', 0, 'a', {'b': "c", 'd:e': "f"}, None, None,
             None, None, 18, '', 18),
            ('<a b="c" d="e" />', 0, 'a', {'b': "c", 'd': "e"}, None, None,
             None, None, 17, '', 17),
            ('<a b="c/d" e="f"/>', 0, 'a', {'b': "c/d", 'e': "f"}, None, None,
             None, None, 18, '', 18),
            ('<a b="c>d" e="f"/>', 0, 'a', {'b': "c>d", 'e': "f"}, None, None,
             None, None, 18, '', 18),

            # Comments
            ('<!---->', 0, NewDumbXml.COMMENT, {}, 4, '', '', 4, 7, '', 7),
            ('<!-- hello there -->', 0, NewDumbXml.COMMENT, {}, 4,
             ' hello there ', ' hello there ', 17, 20, '', 20),
            ('<!-- hello there --> tail', 0, NewDumbXml.COMMENT, {}, 4,
             ' hello there ', ' hello there ', 17, 20, ' tail', 25),

            # With content
            ('<a></a>', 0, 'a', {}, 3, '', '', 3, 7, '', 7),
            ('<a></a> tail', 0, 'a', {}, 3, '', '', 3, 7, ' tail', 12),
            ('<a b="c"></a> tail', 0, 'a', {'b': "c"}, 9, '', '', 9, 13,
             ' tail', 18),
            ('<a>hello world</a>', 0, 'a', {}, 3, 'hello world', 'hello world',
             14, 18, '', 18),
            ('<a>hello <![CDATA[</a>]]></a>', 0, 'a', {}, 3,
             'hello <![CDATA[</a>]]>', 'hello <![CDATA[</a>]]>', 25, 29, '',
             29),
            ('<a>hello world</a> tail', 0, 'a', {}, 3, 'hello world',
             'hello world', 14, 18, ' tail', 23),
            ('<a b="c">hello world</a> tail', 0, 'a', {'b': "c"}, 9,
             'hello world', 'hello world', 20, 24, ' tail', 29),
        )
        for case in cases:
            dumb_xml = NewDumbXml(case[0])
            self.assertEquals(
                (dumb_xml.source, dumb_xml.position, dumb_xml.tag,
                 dumb_xml.attrib, dumb_xml.text_position, dumb_xml.text,
                 dumb_xml.content, dumb_xml.content_end,
                 dumb_xml.tail_position, dumb_xml.tail, dumb_xml.end),
                case
            )

    def test_no_embeds_errors(self):
        cases = (('<a', "Opening tag not closed on line 1"),
                 ('<a b="c"', "Opening tag 'a' not closed on line 1"),
                 ('<a', "Opening tag not closed on line 1"),
                 ('<a/', "Opening tag 'a' not closed on line 1"),
                 ('<a /', "Opening tag 'a' not closed on line 1"),
                 ('<a/oiajod', "Opening tag 'a' not closed on line 1"),
                 ('<a>', "Tag 'a' not closed on line 1"),
                 ('<a>hello world', "Tag 'a' not closed on line 1"),
                 ('<!---', "Comment not closed on line 1"),
                 ('<!--jafosijdfoas-', "Comment not closed on line 1"))
        for source, error_msg in cases:
            with self.assertRaisesRegexp(DumbXmlSyntaxError,
                                         r'^{}$'.format(re.escape(error_msg))):
                dumb_xml = NewDumbXml(source)
                dumb_xml.end  # should expand all properties eventually

    def test_one_child(self):
        cases = (
            # Without content
            ('<r><a/></r>', '<a/>', 7, 3, 'a', {}, None, None, 7, '', 7),
            ('<r><a:b/></r>', '<a:b/>', 9, 3, 'a:b', {}, None, None, 9, '', 9),
            ('<r> <a/></r>', ' <a/>', 8, 4, 'a', {}, None, None, 8, '', 8),
            ('<r><a /></r>', '<a />', 8, 3, 'a', {}, None, None, 8, '', 8),
            ('<r><a/ ></r>', '<a/ >', 8, 3, 'a', {}, None, None, 8, '', 8),
            ('<r><a/> tail</r>', '<a/> tail', 12, 3, 'a', {}, None, None, 7,
             ' tail', 12),
            ('<r><a b="c" d:e="f"/></r>', '<a b="c" d:e="f"/>', 21, 3, 'a',
             {'b': "c", 'd:e': "f"}, None, None, 21, '', 21),
            ('<r><a b="c" d="e" /></r>', '<a b="c" d="e" />', 20, 3, 'a',
             {'b': "c", 'd': "e"}, None, None, 20, '', 20),
            ('<r><a b="c/d" e="f"/></r>', '<a b="c/d" e="f"/>', 21, 3, 'a',
             {'b': "c/d", 'e': "f"}, None, None, 21, '', 21),
            ('<r><a b="c>d" e="f"/></r>', '<a b="c>d" e="f"/>', 21, 3, 'a',
             {'b': "c>d", 'e': "f"}, None, None, 21, '', 21),

            # Comments
            ('<r><!----></r>', '<!---->', 10, 3, NewDumbXml.COMMENT, {}, 7, '',
             10, '', 10),
            ('<r><!-- hello there --></r>', '<!-- hello there -->', 23, 3,
             NewDumbXml.COMMENT, {}, 7, ' hello there ', 23, '', 23),
            ('<r><!-- hello there --> tail</r>', '<!-- hello there --> tail',
             28, 3, NewDumbXml.COMMENT, {}, 7, ' hello there ', 23, ' tail',
             28),

            # With content
            ('<r><a></a></r>', '<a></a>', 10, 3, 'a', {}, 6, '', 10, '', 10),
            ('<r><a></a> tail</r>', '<a></a> tail', 15, 3, 'a', {}, 6, '', 10,
             ' tail', 15),
            ('<r><a b="c"></a> tail</r>', '<a b="c"></a> tail', 21, 3, 'a',
             {'b': "c"}, 12, '', 16, ' tail', 21),
            ('<r><a>hello world</a></r>', '<a>hello world</a>', 21, 3, 'a', {},
             6, 'hello world', 21, '', 21),
            ('<r><a>hello <![CDATA[</a>]]></a></r>',
             '<a>hello <![CDATA[</a>]]></a>', 32, 3, 'a', {}, 6,
             'hello <![CDATA[</a>]]>', 32, '', 32),
            ('<r><a>hello world</a> tail</r>', '<a>hello world</a> tail', 26,
             3, 'a', {}, 6, 'hello world', 21, ' tail', 26),
            ('<r><a b="c">hello world</a> tail</r>',
             '<a b="c">hello world</a> tail', 32, 3, 'a', {'b': "c"}, 12,
             'hello world', 27, ' tail', 32),
        )
        for case in cases:
            root = NewDumbXml(case[0])
            children = list(root)
            self.assertEquals(len(children), 1)
            inner = children[0]
            self.assertEquals(
                (inner.source, root.content, root.content_end, inner.position,
                 inner.tag, inner.attrib, inner.text_position, inner.text,
                 inner.tail_position, inner.tail, inner.end),
                case
            )

    def test_several_children(self):
        cases = (
            ['<a />', None],
            ['<a><b/><c>hello world</c></a >', '<b/><c>hello world</c>',
             '<b/>', '<c>hello world</c>'],
            ['<a><b/><c>hello world</c></a>', '<b/><c>hello world</c>', '<b/>',
             '<c>hello world</c>'],
            ['<a><b c="d"/><e>hello world</e></a>',
             '<b c="d"/><e>hello world</e>', '<b c="d"/>',
             '<e>hello world</e>'],
            ['<a><b/><c d="e">hello world</c></a>',
             '<b/><c d="e">hello world</c>', '<b/>',
             '<c d="e">hello world</c>'],
            ['<a><b><c /></b></a>', '<b><c /></b>', '<b><c /></b>'],
            ['<a><b><c /></b><d /></a>', '<b><c /></b><d />', '<b><c /></b>',
             '<d />'],
        )
        for case in cases:
            root_source = case[0]
            content = case[1]
            children_sources = case[2:]
            root = NewDumbXml(root_source)
            self.assertEquals(root.content, content)
            self.assertEquals(
                [inner.source[inner.position:inner.end] for inner in root],
                children_sources
            )

    def test_iter_errors(self):
        cases = (
            ('<a></b>',
             "Closing tag 'b' does not match opening tag 'a' on line 1"),
            ('<a></a', "Invalid closing of tag 'a' on line 1"),
            ('<a></a aosdjfio', "Invalid closing of tag 'a' on line 1"),
        )
        for source, error_msg in cases:
            with self.assertRaisesRegexp(DumbXmlSyntaxError,
                                         r'^{}$'.format(re.escape(error_msg))):
                list(NewDumbXml(source))

    def test_inbetweens(self):
        root = NewDumbXml('<a>This<b/>is<c/>separated<d/>by<e/>tags</a>')
        collected = [root.text]
        for inner in root:
            collected.append(inner.tail)
        self.assertEquals(root.content,
                          'This<b/>is<c/>separated<d/>by<e/>tags')
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

    def test_find_children_multitag(self):
        root = NewDumbXml("""
            <root>
                <a>AAA</a>
                <b>BBB</b>
                <c>CCC</c>
            </root>
        """)
        self.assertEquals(
            [(inner.tag, inner.attrib, inner.text)
             for inner in root.find_children('a', 'b')],
            [('a', {}, "AAA"),
             ('b', {}, "BBB")]
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

    def test_find_descendants_multitag(self):
        root = NewDumbXml("""
            <root>
                <a>first child</a>
                <b>
                    <a>first grandchild</a>
                    <c>second grandchild</c>
                </b>
            </root>
        """)
        self.assertEquals(
            [(inner.tag, inner.attrib, inner.text)
             for inner in root.find_descendants('a', 'c')],
            [('a', {}, "first child"),
             ('a', {}, "first grandchild"),
             ('c', {}, "second grandchild")]
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
