from openformats.formats.android import AndroidHandler


class AndroidUnescapedHandler(AndroidHandler):
    @staticmethod
    def escape(string):
        string = AndroidHandler.escape(string)
        return (
            string.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "\\n")
            .replace("\t", "\\t")
            .replace("@", "\\@")
            .replace("?", "\\?")
        )

    @staticmethod
    def unescape(string):
        string = AndroidHandler.unescape(string)
        return (
            string.replace("\\?", "?")
            .replace("\\@", "@")
            .replace("\\t", "\t")
            .replace("\\n", "\n")
            .replace("&gt;", ">")
            .replace("&lt;", "<")
            .replace("&amp;", "&")
        )
