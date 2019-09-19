from __future__ import absolute_import

import io
import re
import unicodedata
import zipfile
from itertools import count

import six
from lxml import etree

from openformats.handlers import Handler
from openformats.strings import OpenString
from openformats.transcribers import Transcriber
from openformats.utils.compat import ensure_unicode


class InDesignHandler(Handler):
    """ A handler class that parses and compiles .idml files that are created
        in Adobe's InDesign.

        IDML files contain multiple XML fragments that can be parsed to extract
        strings from.
    """

    name = "InDesign"
    extension = "idml"
    SPECIFIER = None
    PROCESSES_BINARY = True
    EXTRACTS_RAW = False

    # The ? at the end of the string regex, makes it non-greedy in order to
    # allow trailing spaces to be preserved
    CONTENT_REGEX = r'(<Content>\s*)(.*?)(\s*</Content>)'
    SPECIAL_CHARACTERS_REGEX = re.compile(
        ensure_unicode(r'<\?ACE \d+\?>|<Br/>;')
    )

    def __init__(self, *args, **kwargs):
        self.order_gen = count()
        self.stringset = []

    def parse(self, content, **kwargs):
        """ Parses .idml file content and returns the resource template and
            stringset.
            * Find all Story fragments based on the contents of 'designmap.xml'
            * Parse all Story fragments to extract the translatable strings
              and replace them with a replacement hash
            * Copy the source archive into a new one, trying to preserve as
              much of the structure and content as possible, but replacing the
              story fragments with the templates
            * Return the (template, stringset) tuple
        """

        template_dict = {}
        file_in = io.BytesIO(content)
        zipfile_in = zipfile.ZipFile(file_in)
        filenames = self._get_story_filenames(zipfile_in)

        for filename in filenames:
            story = zipfile_in.read(filename).decode('utf-8')
            template_dict[filename] = self._find_and_replace(story)

        template = self._make_zipfile_copy(zipfile_in, template_dict)
        return template, self.stringset

    def _find_and_replace(self, story_xml):
        """ Finds all the translatable content in the given XML string
            replaces it with the string_hash and returns the resulting
            template while updating `self.stringset` in the process.
            args:
                story_xml (str): The xml content of a single Story of the IDML
                file
            returns:
                the input string with all translatable content replaced by the
                md5 hash of the string.
        """
        template = re.sub(ensure_unicode(self.CONTENT_REGEX),
                          self._replace,
                          story_xml)
        return template

    def _replace(self, match):
        """ Implements the logic used by `self.CONTENT_REGEX.sub(...)` to
            replace strings with their template replacement and appends new
            strings to `self.stringset`.
        """
        opening_tag, string, closing_tag = match.groups()

        if self._can_skip_content(string):
            return match.group()
        order = next(self.order_gen)
        string_object = OpenString(six.text_type(order), string, order=order)
        self.stringset.append(string_object)
        return u"".join((opening_tag, string_object.template_replacement,
                         closing_tag))

    def _can_skip_content(self, string):
        """ Checks if the contents of an XML files are translateable.
            Strings that contain only special characters or can be evaluated
            to a nunber are skipped.
        """
        stripped_string = re.\
            sub(ensure_unicode(self.SPECIAL_CHARACTERS_REGEX), u'', string).\
            strip()
        if not stripped_string:
            return True
        try:
            float(string.strip())
            return True
        except ValueError:
            pass
        if not self._contains_translatable_character(stripped_string):
            return True
        return False

    def _contains_translatable_character(self, string):
        """ Checks if a string contains at least one character that can be
            translated. We assume that translatable characters are the letters,
            the symbols and the punctuation.
        """

        LETTER, PUNCTUATION, SYMBOL = 'L', 'P', 'S'
        for letter in string:
            char_type = unicodedata.category(letter)
            if char_type[0] in (LETTER, PUNCTUATION, SYMBOL):
                return True
        return False

    def compile(self, template, stringset, **kwargs):
        """ Compiles .idml template against the stringset and returns the
            compiled file.
            * Find all Story fragments based on the contents of 'designmap.xml'
            * Find hashes from the stringset within the Story fragments and
              replace them with the translations
            * Replace hashes that weren't found with empty strings
            * Copy the template archive into a new one, trying to preserve as
              much of the structure and content as possible, but replacing the
              story fragments with the compiled ones
            * Return the compiled archive
        """

        self.stringset, compiled_dict = iter(stringset), {}
        self.string = next(self.stringset)
        file_in = io.BytesIO(template)
        zipfile_in = zipfile.ZipFile(file_in)
        filenames = self._get_story_filenames(zipfile_in)
        for filename in filenames:
            template = zipfile_in.read(filename).decode('utf8')
            compiled_dict[filename] = self._compile_story(template)

        return self._make_zipfile_copy(zipfile_in, compiled_dict)

    def _compile_story(self, template):
        """ Handles the compilation of a single story
            args:
                story_content: the xml content of the story
            returns:
                compiled_story: the compiled story content
        """

        transcriber = Transcriber(template)
        template = transcriber.source
        hash_regex = re.compile(ensure_unicode(r'[a-z,0-9]{32}_tr'))
        while self.string is not None:
            try:
                hash_position = template.index(
                    self.string.template_replacement
                )
            except (ValueError, IndexError):
                break
            else:
                transcriber.copy_until(hash_position)
                transcriber.add(self.string.string)
                transcriber.skip(len(self.string.template_replacement))
                self.string = next(self.stringset, None)

        transcriber.copy_to_end()
        compiled = transcriber.get_destination()
        compiled = hash_regex.sub(u'', compiled)
        return compiled

    @staticmethod
    def _get_story_filenames(zipfile_in):
        """ Find the filenames of all the Story fragments within the archive
            that must be parsed/compiled. The files are the intersection of:

            * The keys that are in the 'StoryList' attribute of the root XML
              node in 'designmap.xml'
            * All the filenames in the archive

            The rest of the files in the archive are meant to be left
            untouched.
        """

        designmap = etree.fromstring(
            zipfile_in.read('designmap.xml'),
            parser=etree.XMLParser(resolve_entities=False),
        )
        story_keys = {'Stories/Story_{}.xml'.format(key)
                      for key in designmap.attrib.get('StoryList', "").split()}
        return sorted(story_keys & set(zipfile_in.namelist()))

    @staticmethod
    def _make_zipfile_copy(zipfile_in, data):
        """ Copy most of 'zipfile_in' to a new zip file. If a filename in
            'zipfile_in' exists as a key in 'data', then instead of copying
            that file from 'zipfile_in', write the relevant value from 'data'.

            Return the byte contents of the new zipfile.
        """

        file_out = io.BytesIO()
        zipfile_out = zipfile.ZipFile(file_out, 'w')
        for filename in zipfile_in.namelist():
            info = zipfile_in.getinfo(filename)
            if filename in data:
                zipfile_out.writestr(info, data[filename].encode('utf8'))
            else:
                zipfile_out.writestr(info, zipfile_in.read(filename))
        zipfile_out.close()
        file_out.seek(0)  # Reset the "cursor" for `read` to return everything
        return file_out.read()
