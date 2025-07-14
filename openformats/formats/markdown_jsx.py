from openformats.formats.github_markdown_v2 import GithubMarkdownHandlerV2
from openformats.handlers import Handler


class MarkdownJsxHandler(GithubMarkdownHandlerV2, Handler):
    name = "Markdown_JSX"
    extension = "mdx"
