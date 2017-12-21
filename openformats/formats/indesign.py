from __future__ import absolute_import

from base64 import b64encode, b64decode
import io

from bs4 import BeautifulSoup
from ucf import UCF

from ..handlers import Handler
from ..strings import OpenString


class InDesignHandler(Handler):
    """A handler class that parses and compiles .idml files that are created
    in Adobe's InDesign.

    IDML files contain multiple XML fragments that can be parsed to extract
    strings from.
    """

    name = "InDesign"
    extension = "idml"
    SPECIFIER = None

    def bind_content(self, content):
        self.content = content

    def bind_file(self, filename):
        with open(filename) as f:
            self.content = f.read()

    """ Parse Methods """

    def parse(self, content, **kwargs):
        stringset = []
        order = 0

        # The content is a base64 encoded IDML file
        idml = UCF(io.BytesIO(b64decode(content)))

        # Iterate over the contents of the IDML file
        for key in idml.keys():
            if not key.startswith("Stories/"):
                continue
            soup = BeautifulSoup(idml[key], "xml")
            replacements = []
            # First, we save the strings to the string-set. We don't alter the
            # XML DOM contents because is will cause the for loops to process
            # the newly altered content too
            for content in self._get_all_contents(soup):
                for string in content.stripped_strings:
                    string_object = OpenString(str(order), string, order=order)
                    stringset.append(string_object)
                    replacements.append(string_object.template_replacement)
                    order += 1

            # Reiterate over the XML and replace the original strings with
            # their template replacements
            for content in self._get_all_contents(soup):
                for string in list(content.stripped_strings):
                    replacement = replacements.pop(0)
                    content.string = content.string.replace(string,
                                                            replacement, 1)

            # Update the XML file to contain the template strings
            idml[key] = str(soup)

        out = io.BytesIO()
        idml.save(out)
        template = b64encode(out.getvalue())

        return template, stringset

    def _get_all_contents(self, idml):
        """Return an array with all the strings of an IDML file."""
        for story in idml.find_all("Story"):
            for content in story.find_all("Content"):
                yield content

    """ Compile Methods """

    def compile(self, template, stringset, **kwargs):
        # The content is a base64 encoded IDML file
        idml = UCF(io.BytesIO(b64decode(template)))

        _stringset = list(stringset)

        # Iterate over the contents of the IDML file
        for key in idml.keys():
            if not key.startswith("Stories/"):
                continue
            soup = BeautifulSoup(idml[key], "xml")
            translations = []
            # First, we save the strings to the string-set. We don't alter the
            # XML DOM contents because is will cause the for loops to process
            # the newly altered content too
            for content in self._get_all_contents(soup):
                for template in content.stripped_strings:
                    translation = self._get_translation(template, _stringset)
                    translations.append(translation)

            # Reiterate over the XML and replace the original strings with
            # their template replacements
            for content in self._get_all_contents(soup):
                strings = list(content.stripped_strings)
                for temp in strings:
                    translation = translations.pop(0)
                    content.string = content.string.replace(temp,
                                                            translation, 1)

            # Update the XML file to contain the template strings
            idml[key] = str(soup)

        out = io.BytesIO()
        idml.save(out)

        return out.getvalue()

    def _get_translation(self, template, stringset):
        """Get the translation of a template placeholder."""
        for string in stringset:
            if string.template_replacement == template:
                # stringset.remove(string)
                return string.string
        print "Template %s not found" % template
