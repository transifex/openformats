---
title: el:About writing and formatting on GitHub
intro: {{ site.data.guides.dotcom-writing-on-github.shortdesc.about-writing-and-formatting-on-github }}
---

el:[Markdown](http://daringfireball.net/projects/markdown/) is an easy-to-read, easy-to-write syntax for formatting plain text.

el:[![Electron Logo](http://electron.atom.io/images/electron-logo.svg)](http://electron.atom.io/)

el:[![Travis Build Status](https://travis-ci.org/electron/electron.svg?branch=master)](https://travis-ci.org/electron/electron)
[![AppVeyor Build Status](https://ci.appveyor.com/api/projects/status/kvxe4byi7jcxbe26/branch/master?svg=true)](https://ci.appveyor.com/project/Atom/electron)
[![devDependency Status](https://david-dm.org/electron/electron/dev-status.svg)](https://david-dm.org/electron/electron?type=dev)
[![Join the Electron Community on Slack](http://atom-slack.herokuapp.com/badge.svg)](http://atom-slack.herokuapp.com/)

el::memo: Available Translations: [Korean](https://github.com/electron/electron/tree/master/docs-translations/ko-KR/project/README.md) | [Simplified Chinese](https://github.com/electron/electron/tree/master/docs-translations/zh-CN/project/README.md) | [Brazilian Portuguese](https://github.com/electron/electron/tree/master/docs-translations/pt-BR/project/README.md) | [Traditional Chinese](https://github.com/electron/electron/tree/master/docs-translations/zh-TW/project/README.md)

el:The Electron framework lets you write cross-platform desktop applications
using JavaScript, HTML and CSS. It is based on [Node.js](https://nodejs.org/) and
[Chromium](http://www.chromium.org) and is used by the [Atom
editor](https://github.com/atom/atom) and many other [apps](http://electron.atom.io/apps).

el:Follow [@ElectronJS](https://twitter.com/electronjs) on Twitter for important
announcements.

el:This project adheres to the Contributor Covenant [code of conduct](CODE_OF_CONDUCT.md).
By participating, you are expected to uphold this code. Please report unacceptable
behavior to electron@github.com.

{% if page.version == 'dotcom' or page.version == 'cloud' or page.version > 2.5 %}

### el:Text formatting toolbar

el:Every comment field on {{ site.data.variables.product.product_name }} contains a text formatting toolbar, allowing you to format your text without learning Markdown syntax. In addition to Markdown formatting like bold and italic styles and creating headers, links, and lists, the toolbar includes {{ site.data.variables.product.product_name }}-specific features such as @mentions, task lists, and links to issues and pull requests.

el:![Markdown toolbar](/assets/images/help/writing/markdown-toolbar.gif)

{% endif %}

### el:What's happening here?
el:Take a closer look at the `docker-compose.windows.yml` file.

el:```
version: '3'
services:
  db:
    image: microsoft/mssql-server-windows-express
    environment:
      sa_password: "Password1"
    ports:
      - "1433:1433" # for debug. Remove this for production

  web:
    build:
      context: .
      dockerfile: Dockerfile.windows
    environment:
      - "Data:DefaultConnection:ConnectionString=Server=db,1433;Database=MusicStore;User Id=sa;Password=Password1;MultipleActiveResultSets=True"
    depends_on:
      - "db"
    ports:
      - "5000:5000"

networks:
  default:
    external:
      name: nat
```

## el:Downloads

el:To install prebuilt Electron binaries, use
[`npm`](https://docs.npmjs.com/):

el:```sh
# Install as a development dependency
npm install electron --save-dev

# Install the `electron` command globally in your $PATH
npm install electron -g
```

el:See the [releases page](https://github.com/electron/electron/releases) for
prebuilt binaries, debug symbols, and more.

### el:Mirrors

- el:[China](https://npm.taobao.org/mirrors/electron)

## el:Documentation

el:Guides and the API reference are located in the
[docs](https://github.com/electron/electron/tree/master/docs) directory. It also
contains documents describing how to build and contribute to Electron.

## el:Documentation Translations

- el:[Brazilian Portuguese](https://github.com/electron/electron/tree/master/docs-translations/pt-BR)
- el:[Korean](https://github.com/electron/electron/tree/master/docs-translations/ko-KR)
- el:[Japanese](https://github.com/electron/electron/tree/master/docs-translations/jp)
- el:[Spanish](https://github.com/electron/electron/tree/master/docs-translations/es)
- el:[Simplified Chinese](https://github.com/electron/electron/tree/master/docs-translations/zh-CN)
- el:[Traditional Chinese](https://github.com/electron/electron/tree/master/docs-translations/zh-TW)
- el:[Turkish](https://github.com/electron/electron/tree/master/docs-translations/tr-TR)
- el:[Thai](https://github.com/electron/electron/tree/master/docs-Translations/th-TH)
- el:[Ukrainian](https://github.com/electron/electron/tree/master/docs-translations/uk-UA)
- el:[Russian](https://github.com/electron/electron/tree/master/docs-translations/ru-RU)
- el:[French](https://github.com/electron/electron/tree/master/docs-translations/fr-FR)

## el:Quick Start

el:Clone and run the [`electron/electron-quick-start`](https://github.com/electron/electron-quick-start)
repository to see a minimal Electron app in action.

## el:Community

el:You can ask questions and interact with the community in the following
locations:
- el:[`electron`](http://discuss.atom.io/c/electron) category on the Atom
el:forums
- el:`#atom-shell` channel on Freenode
- el:[`Atom`](http://atom-slack.herokuapp.com/) channel on Slack
- el:[`electron-br`](https://electron-br.slack.com) *(Brazilian Portuguese)*
- el:[`electron-kr`](http://www.meetup.com/electron-kr/) *(Korean)*
- el:[`electron-jp`](https://electron-jp.slack.com) *(Japanese)*
- el:[`electron-tr`](http://www.meetup.com/Electron-JS-Istanbul/) *(Turkish)*
- el:[`electron-id`](https://electron-id.slack.com) *(Indonesia)*

el:Check out [awesome-electron](https://github.com/sindresorhus/awesome-electron)
for a community maintained list of useful example apps, tools and resources.


### el:Further reading

- "[el:Basic writing and formatting syntax](/articles/basic-writing-and-formatting-syntax)"
- "[el:Working with advanced formatting](/articles/working-with-advanced-formatting)"
- "[el:Mastering Markdown](https://guides.github.com/features/mastering-markdown/)"
- "[el:Markdown Tutorial](http://markdowntutorial.com/)"

## el:License

el:[MIT](https://github.com/electron/electron/blob/master/LICENSE)

el:When using the Electron or other GitHub logos, be sure to follow the [GitHub logo guidelines](https://github.com/logos).

[el:Reference]: http://example.com/
