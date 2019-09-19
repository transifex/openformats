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
        f_in = io.BytesIO(content)
        z_in = zipfile.ZipFile(f_in)
        filenames = self._get_story_filenames(z_in)

        for filename in filenames:
            story = z_in.read(filename).decode('utf-8')
            template_dict[filename] = self._find_and_replace(story)

        f_out = io.BytesIO()
        z_out = zipfile.ZipFile(f_out, 'w')
        for filename in z_in.namelist():
            z_out.writestr(z_in.getinfo(filename),
                           template_dict.get(filename, z_in.read(filename)))
        z_out.close()
        f_out.seek(0)
        return f_out.read(), self.stringset

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

        for letter in string:
            char_type = unicodedata.category(letter)
            if char_type[0] in ("L", "P", "S"):
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
        f_in = io.BytesIO(template)
        z_in = zipfile.ZipFile(f_in)
        filenames = self._get_story_filenames(z_in)
        for filename in filenames:
            template = z_in.read(filename).decode('utf8')
            compiled_dict[filename] = self._compile_story(template)

        f_out = io.BytesIO()
        z_out = zipfile.ZipFile(f_out, 'w')
        for filename in z_in.namelist():
            info = z_in.getinfo(filename)
            if filename in compiled_dict:
                z_out.writestr(info, compiled_dict[filename].encode('utf8'))
            else:
                z_out.writestr(info, z_in.read(filename))
        z_out.close()
        f_out.seek(0)
        return f_out.read()

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
    def _get_story_filenames(z_in):
        """ Find the filenames of all Story fragmens by intersecting the list
            of keys of the 'StoryList' attribute of the top node in
            'designmap.xml' with the filenames within the archive that refer to
            Story fragments.
        """

        designmap = etree.fromstring(
            z_in.read('designmap.xml'),
            parser=etree.XMLParser(resolve_entities=False),
        )
        story_keys = {'Stories/Story_{}.xml'.format(key)
                      for key in designmap.attrib.get('StoryList', "").split()}
        return sorted(story_keys & set(z_in.namelist()))
