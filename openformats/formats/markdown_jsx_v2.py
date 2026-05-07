from openformats.formats.github_markdown_v2_1 import GithubMarkdownHandlerV2_1
from openformats.handlers import Handler


class MarkdownJsxHandler_v2(GithubMarkdownHandlerV2_1, Handler):
    name = "Markdown_JSX_v2"
    extension = "mdx"
