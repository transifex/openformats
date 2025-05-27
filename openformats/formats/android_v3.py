from __future__ import absolute_import
import re
from hashlib import md5
from openformats.exceptions import ParseError
from openformats.formats.android_unescaped import AndroidUnescapedHandler
from ..utils.xml import NewDumbXml as DumbXml
import six

import re

import six

from openformats.exceptions import ParseError

from ..utils.xml import NewDumbXml as DumbXml


class AndroidDumbXml(DumbXml):
    DumbXml = DumbXml
    def __init__(self, source, start=0):
        super(AndroidDumbXml, self).__init__(source, start)
        self.string_with_cdata = set()

   
    def _find_next_lt(self, start):
        in_cdata = False
        for ptr in six.moves.xrange(start, len(self.source)):
            candidate = self.source[ptr]
            if in_cdata:
                if (candidate == ']' and
                        self.source[ptr:ptr + len("]]>")] == "]]>"):
                    in_cdata = False
            else:
                if candidate == self.LESS_THAN:
                    # Check against CDATA
                    if self.source[ptr:ptr + len("<![CDATA[")] == "<![CDATA[":
                        # this is the only difference from the parent class,
                        # move the text position to the start of the cdata
                        self._text_position=ptr+len("<![CDATA[")
                        in_cdata = True
                    else:
                        return ptr
        # We reached the end of the string, lets return accordingly
        return len(self.source)
    
    @property
    def content(self):
        """ All the contents of a tag (both text and children tags)
             Parent class:
             <string><![CDATA[goobye <b>cruel</b> world]]></string>
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            
            This class:
            <string><![CDATA[goobye <b>cruel</b> world]]></string>
                             ^^^^^^^^^^^^^^^^^^^^^^^^^
        """

        if self.tag == self.COMMENT:
            return self.text
        if self.content_end is None:
            return None
        _string_value = self.source[self.text_position:self.content_end]
        if _string_value.strip().endswith("]]>"):
            diff = len(_string_value) -len(_string_value.strip())
            self._content_end = self.content_end-diff if diff>0 else self.content_end
            _string_value = self.source[self.text_position:self.content_end-len("]]>")]
            self.string_with_cdata.add(self._attrib.get("name"))
        return _string_value
    


class AndroidHandlerv3(AndroidUnescapedHandler):
    PLURAL_TEMPLATE_CDATA = u'<item quantity="{rule}"><![CDATA[{string}]]></item>'
    XmlClass = AndroidDumbXml

    def __init__(self):
        super(AndroidHandlerv3, self).__init__()
        self.cdata_pattern = re.compile(r'!\[CDATA')
    
    def _handle_string(self, child):
        """Handles child element that has the `string` tag.

        If it contains a string it will create an OpenString object.

        :returns: An list of containing the OpenString object
                    if one was created else it returns None.
        """
        name, product = self._get_child_attributes(child)
        
        content = child.content
        tx_comment = "\nAdded by Transifex:CDATA"
        developer_comment = self.current_comment +tx_comment if name in child.string_with_cdata else self.current_comment
        string = self._create_string(
            name,
            content,
            developer_comment,
            product,
            child
        )
        if string is not None:
            # <string>My Text</string>
            #         ^
            self.transcriber.copy_until(child.text_position)
            self.transcriber.add(string.template_replacement)
            # <string>My Text</string>
            #                ^
            self.transcriber.skip(len(child.content))
            return [string]
        return None
   
    def _handle_string_plural(self, child):
        """Handles child element that has the `plurals` tag.

        It will find children with the `item` tag and create an OpenString
        object out of them.

        :raises: Parse error if the `quantity` attribute is missing from any
                    of the child's children
        :returns: An list containing the OpenString object if one was created
                    else None.
        """

        string_rules_text = {}
        item_iterator = child.find_children()
        # Iterate through the children with the item tag.
        
        try:
            has_cdata = False if self.cdata_pattern.search(child.content) is None else True
        except TypeError:
            raise ParseError("No plurals found in <plurals> tag on line 1")
        
        for item_tag in item_iterator:
            if item_tag.tag != self.XmlClass.COMMENT:
                rule_number = self._validate_plural_item(item_tag)
                string_rules_text[rule_number] = item_tag.content

        name, product = self._get_child_attributes(child)
      
        string = self._create_string(
            name,
            string_rules_text,
            self.current_comment,
            product,
            child,
            # <plurals> tags always define plurals, even if the language has
            # one plural form and thus there's only one <item>
            pluralized=True,
        )
      
        if string is not None:
            # <plurals name="foo">   <item>Hello ...
            #                        ^
            first_plural_position = child.text_position + len(child.text or '')
            self.transcriber.copy_until(first_plural_position)
            
            self.transcriber.add(string.template_replacement if not has_cdata else string.template_replacement + "_cdata")
            # ...</item>   </plurals>...
            #           ^
            self.transcriber.skip_until(item_tag.tail_position)
            # FYI: item_tag is the last iterated item from the loop before.
            return [string]
        return None


    """ Compile Methods """

   


    
    def _search_for_cdata(self,_string,_destination):
        """
        The destination list is the entries that the transcriber
        has visited. The last string is the one that is being compiled.
        An example entry is:
        <string name="string_key"><![CDATA[hello]]></string>
        the transcriber will have the following entries:
        [ <string name="string_key"><![CDATA[],
          hello]
        so we need to find if the preceding entry of the 
        actual string is a cdata entry and return True/False
        """
        if not _destination or (len(_destination)> 0 and _destination[-1] != _string):
            return False
        try:
            return bool(self.cdata_pattern.search(_destination[-2]))
        except TypeError:
            return False
        
        
    def _compile_string(self, child):
        """Handles child element that has the `string` and `item` tag.

        It will compile the tag if matching string exists. Otherwise it will
        skip it.
        """
       

        if self._should_compile(child):
           
            self.transcriber.copy_until(child.text_position)
            _string = self.next_string.string
            self.transcriber.add(_string)
           
            has_cdata = self._search_for_cdata(_string, self.transcriber.destination)
            self.transcriber.skip_until(child.content_end if not has_cdata else child.content_end-len("]]>"))
            self.transcriber.copy_until(child.tail_position)
            self.transcriber.mark_section_start()
            self.transcriber.copy_until(child.end)
            self.transcriber.mark_section_end()
            self.next_string = self._get_next_string()
        elif not child.text:
            # In the case of a string-array we don't want to skip an
            # empty array element that was initially empty.
            pass
        else:
            self._skip_tag(child)
       


    def _compile_string_plural(self, child):
        """Handles child element that has the `plurals` tag.

        It will check if pluralized string exists and add every plural as an
        `item` child. If no matching string is found it will remove the tag.

        :NOTE: If the `plurals` had empty `item` tags to begin with we leave
                it as it is.
        """
        # If placeholder (has empty children) skip
        if len(list(child.find_children(self.STRING_ITEM))):
            return
       
        if self._should_compile(child):
            self.transcriber.copy_until(child.text_position)
          
            has_cdata = child.content.strip().endswith("_cdata")
           
            if has_cdata:
                template_replacement = self.next_string.template_replacement+"_cdata"

                splited_content = child.content.split(
                    template_replacement
                )
            else:
                splited_content = child.content.split(
                    self.next_string.template_replacement
                )
            start = splited_content[0]
            end = splited_content[1]
            
            # If newline formating
            if start.startswith(end):
                start = start.replace(end, '', 1)
                self.transcriber.add(end)
            template = self.PLURAL_TEMPLATE_CDATA if  has_cdata else self.PLURAL_TEMPLATE
           
            for rule, string in six.iteritems(self.next_string.string):
                self.transcriber.add(
                    start +
                    template.format(
                        rule=self.get_rule_string(rule), string=string
                    ) + end
                )
            self.transcriber.skip_until(child.content_end)
            self.transcriber.copy_until(child.end)
            self.next_string = self._get_next_string()
        else:
            self._skip_tag(child)

    def _should_compile(self, child):
        """Checks if the current child should be compiled.

        :param child: The child to check if it should be compiled.
        :returns: True if the child should be compiled else False.
        """
        child_content = child.content and child.content.strip() or ''
    
        if child_content.endswith("_cdata"):     
            child_content = child_content.replace("_cdata", "")
       
        return (
            self.next_string is not None and
            self.next_string.template_replacement == child_content
        )
    





    