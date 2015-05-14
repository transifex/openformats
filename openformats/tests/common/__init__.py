import fnmatch
from os import listdir, path
from os.path import isfile, join


class CommonFormatTestCase(object):

    def __init__(self, *args, **kwargs):
        self.data = {}
        super(CommonFormatTestCase, self).__init__(*args, **kwargs)

    def read_files(self, ftypes=('en', 'tpl', 'fr')):
        """Read 1_en.txt into self.data["1_en"], and same for tpl and fr."""
        
        en_files = []
        for f in listdir(self.TESTFILE_BASE):
            if (isfile(join(self.TESTFILE_BASE, f)) and
                fnmatch.fnmatch(f, '*_en.*')):
                en_files.append(f)
        file_nums = set([f.split("_")[0] for f in en_files])

        for num in file_nums:
            for ftype in ftypes:
                name = "%s_%s" % (num, ftype) # 1_en, 1_fr etc.
                filepath = path.join(self.TESTFILE_BASE, "%s.txt" % name)
                if not isfile(filepath):
                    self.fail("Bad test data: Expected to find %s" % filepath)
                with open(filepath, "r") as myfile:
                    self.data[name] = myfile.read()


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
