
import re


SHIFT_TAGS_ONELINE = "EK"
SHIFT_TAGS_MULTILINE = "FLRÜMQ"
SHIFTTAGS = SHIFT_TAGS_ONELINE + SHIFT_TAGS_MULTILINE

# allowed bibinfo format
BIBINFO_FORMAT = re.compile(r"^(\S+)[-_]([A-Z0-9]*)([vr]?)([a-q]?),?(\d+)$")

class Options:

    DEFAULT_OPTIONS = {"inputfile": None,
                        "parser": "ref",
                        "tokenize": "medium",
                        "preedpunc": "leave",
                        "preedtoken": "delete",
                        "editnum": "delete",
                        "character": "utf",
                        "bibinfo": "both",
                        "illegible": "leave",
                        "doubledash": "delete",
                        "nosyllab": False,
                        "strikethru": "leave",
                        "lineinfo": True,
                        "taggermode": False,
                        "output": None,
                        "nowarnings": False,
                        "allowed": "",
                        "preprocess": None,
                        "checkvalid": False,
                        "nosplitinit": False,
                        "leaveshift": False}

    def __init__(self, **kwargs):
        self.__dict__.update(self.DEFAULT_OPTIONS)
        self.__dict__.update(kwargs)

        # LIST OF ALLOWED CHARACTERS FOR validity check
        ALPHA = set("abcdefghijklmnopqrstuvwxyz")
        self.ALLOWED_CHARACTERS = set('-",.:;\/!?1234567890ßäöüÄÖÜ ') | ALPHA | {c.upper() for c in ALPHA}

        self.allowed = self.ALLOWED_CHARACTERS | set(self.allowed)
        # for r-kuerzung
        self.allowed = set(self.allowed) | set("'")

        # escape character regexp
        # -- everything can be escaped by &, but allowed characters may
        # not be escaped
        self.ESCAPE_CHAR = re.compile(r"&([^" + re.escape("".join(self.allowed)) + r"])")


    def __str__(self):
        return str(self.__dict__)
