---
title: "el:About writing and formatting on GitHub"
intro: "el:into text"
numeric_var: 12.5

# one comment

key1:
  - list_key:
    - "el:li within li"
      # second comment
    - "el:li within li 2"
  - "el:li 2"
key2:
  - object_within_list: "el:value"
  - "el:text with a #hashtag in it"
  - "el:li 5"

description: "el:folded style text
"
custom_vars:
  var1: "el:text: some value"
  var2: "el:literal
style with \"quotes\"
text
"
nested_key_outer:
  nested_key_inner:
    "el:nested_value"

key.with.dots: "el:dot value"

1: "el:integer key"

wrapping:
  at: "el:@something"
  brackets: "el:[Something] else"

---

# el:Markdown stuff

## el:Hearders and bold and italic

el:*This text will be italic* and _This will also be italic_

### el:This is an <h3> tag

el:**This text will be bold** and __This will also be bold__

###### el:This is an <h6> tag

el:_You **can** combine bold and italic_


## el:List

### el:Unordered

* el:Item 1
* el:Item 2
  * el:Item 2a
  * el:Item 2b
  * ```
    Item 2c
    ```

### el:Ordered

1. el:Item 1
1. el:Item 2
1. el:Item 3
   1. el:Item 3a
   1. el:Item 3b
   1. ```
      Item 3c
      ```


## el:Images

el:![GitHub Logo](/images/logo.png)
Format: ![Alt Text](url)


## el:Links

el:http://github.com - automatic!
[GitHub](http://github.com)


## el:Blockquotes

el:As Kanye West said:

el:> We're living the future so
> the present is our past.


## el:Inline code

el:I think you should use an `<addr>` element here instead.


# el:GitHub Flavored Markdown

## el:Tables

el:First Header | el:Second Header
------------ | -------------
el:Content from cell 1 | el:Content from cell 2
el:Content in the first column | el:Content in the second column


## el:Syntax highlighting

el:You can simply indent your code by four spaces:

el:    function fancyAlert(arg) {
      if(arg) {
        $.facebox({div:'#foo'})
      }
    }


# el:Code block inside a list
- el:List item  1
- el:List item 2
el:
      function fancyAlert(arg) {
        if(arg) {
          $.facebox({div:'#foo'})
        }
      }


## el:Task lists

- el:[x] @mentions, #refs, [links](), **formatting**, and <del>tags</del> supported
- el:[x] list syntax required (any unordered or ordered list supported)
- el:[x] this is a complete item
- el:[ ] this is an incomplete item


## el:Strikethrough

el:Any word wrapped with two tildes (like ~~this~~) will appear crossed out.


# el:Custom stuff

## el:Liquid template language

el:You can use liquid template syntax in you markdown file.

{% if version <= '2.6' %}

### el:Old version

el:This is a old version of the {{ site.data.variable.product }} documentation.

{% endif %}


## el:Whole Lines as link or reference

### el:Whole line as links in as list

- "[el:Basic writing and formatting syntax](/articles/basic-writing-and-formatting-syntax)"
- [el:Working with advanced formatting](/articles/working-with-advanced-formatting)

### el:Whole line as links

el:[MIT](/LICENSE)
"[GPL](/LICENSE)"

### el:Whole line as links

el:This is as reference [link][1].

[1]: http://example.com/
[el:Reference]: http://example.com/
"[el:Reference]: http://example.com/"


# el:Special section
el:WARNING! The example shown here seems to break all tests on content that is below the javascript code block, because of the "el:" part that is added before the code block notation. Please keep this at the end of the file.  

el:Here's an example of how you can use syntax highlighting with GitHub Flavored Markdown:

el:```javascript
function fancyAlert(arg) {
  if(arg) {
    $.facebox({div:'#foo'})
  }
}
```
