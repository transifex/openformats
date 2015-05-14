from os import path


class CommonFormatTestCase(object):

    def __init__(self, *args, **kwargs):
        self.data = {}
        super(CommonFormatTestCase, self).__init__(*args, **kwargs)

    def read_files(self, ftypes=('en', 'tpl', 'fr')):
        """Read 1_en.txt into self.data["1_en"], and same for tpl and fr."""
        for ftype in ftypes:
            filename = path.join(self.TESTFILE_BASE, "1_%s.txt" % ftype)
            with open(filename, "r") as myfile:
                self.data["1_%s" % ftype] = myfile.read()

    def setUp(self):
        self.handler = self.HANDLER_CLASS()
        self.read_files()
        super(CommonFormatTestCase, self).setUp()

    def test_template(self):
        """Test that the template created is the same as static one."""
        template, _ = self.handler.parse(self.data["1_en"])
        self.assertEquals(template, self.data["1_tpl"])

    def test_compile(self):
        """Test that import-export is the same as the original file."""
        template, stringset = self.handler.parse(self.data["1_en"])
        compiled = self.handler.compile(template, stringset)
        self.assertEquals(compiled, self.data["1_en"])
