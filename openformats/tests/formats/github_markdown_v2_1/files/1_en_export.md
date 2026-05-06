---
title: About writing and formatting on GitHub
intro: into text
numeric_var: 12.5

# one comment

key1:
  - list_key:
    - li within li
      # second comment
    - li within li 2
  - li 2
key2:
  - object_within_list: value
  - "text with a #hashtag in it"
  - li 5

description: >
folded style text
custom_vars:
  var1: "text: some value"
  var2: |
literal
style with "quotes"
text
nested_key_outer:
  nested_key_inner:
    nested_value

key.with.dots: dot value

1: integer key

wrapping:
  at: "@something"
  brackets: "[Something] else"

---

# Markdown stuff

## Hearders and bold and italic

*This text will be italic* and _This will also be italic_

### This is an <h3> tag

**This text will be bold** and __This will also be bold__

###### This is an <h6> tag

_You **can** combine bold and italic_


## List

### Unordered

* Item 1
* Item 2
  * Item 2a
  * Item 2b
  * ```
    Item 2c
    ```

### Ordered

1. Item 1
1. Item 2
1. Item 3
   1. Item 3a
   1. Item 3b
   1. ```
      Item 3c
      ```


## Images

![GitHub Logo](/images/logo.png)
Format: ![Alt Text](url)


## Links

http://github.com - automatic!
[GitHub](http://github.com)


## Blockquotes

As Kanye West said:

> We're living the future so
> the present is our past.


## Inline code

I think you should use an `<addr>` element here instead.


# GitHub Flavored Markdown

## Tables

First Header | Second Header
------------ | -------------
Content from cell 1 | Content from cell 2
Content in the first column | Content in the second column


## Syntax highlighting

You can simply indent your code by four spaces:

    function fancyAlert(arg) {
      if(arg) {
        $.facebox({div:'#foo'})
      }
    }


# Code block inside a list
- List item  1
- List item 2

      function fancyAlert(arg) {
        if(arg) {
          $.facebox({div:'#foo'})
        }
      }


## Task lists

- [x] @mentions, #refs, [links](), **formatting**, and <del>tags</del> supported
- [x] list syntax required (any unordered or ordered list supported)
- [x] this is a complete item
- [ ] this is an incomplete item


## Strikethrough

Any word wrapped with two tildes (like ~~this~~) will appear crossed out.


# Custom stuff

## Liquid template language

You can use liquid template syntax in you markdown file.

{% if version <= '2.6' %}

### Old version

This is a old version of the {{ site.data.variable.product }} documentation.

{% endif %}


## Whole Lines as link or reference

### Whole line as links in as list

- "[Basic writing and formatting syntax](/articles/basic-writing-and-formatting-syntax)"
- [Working with advanced formatting](/articles/working-with-advanced-formatting)

### Whole line as links

[MIT](/LICENSE)
"[GPL](/LICENSE)"

### Whole line as links

This is as reference [link][1].

[1]: http://example.com/
[Reference]: http://example.com/
"[Reference]: http://example.com/"


# Special section
WARNING! The example shown here seems to break all tests on content that is below the javascript code block, because of the "el:" part that is added before the code block notation. Please keep this at the end of the file.  

Here's an example of how you can use syntax highlighting with GitHub Flavored Markdown:

```javascript
function fancyAlert(arg) {
  if(arg) {
    $.facebox({div:'#foo'})
  }
}
```
