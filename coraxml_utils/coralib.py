
from coraxml_utils.settings import *


class Document:

    def __init__(self, sigle, name, header, pages, tokens, shifttags=None):
        self.sigle = sigle
        self.name = name
        self.header = header

        self.pages = pages
        self.tokens = tokens
        self.shifttags = shifttags if shifttags else []

    def __bool__(self):
        return bool(self.pages and self.tokens)


class Page:

    c = 0

    def __init__(self, name, side, columns, extid=""):
        Page.c += 1
        self._id = "p{0}".format(Page.c)
        self.id = extid if extid else ""
        self.name = name
        self.side = side
        self.columns = columns

    def __bool__(self):
        return bool(self.columns)

    def range(self):
        if len(self.columns) > 1:
            first, *_, last = self.columns
            return "{0}..{1}".format(first.id, last.id)
        else:
            first = self.columns[0]
            return first.id


class Column:

    c = 0

    def __init__(self, name, lines, extid=""):
        Column.c += 1
        self._id = "c{0}".format(Column.c)
        self.id = extid if extid else ""
        self.name = name
        self.lines = lines

    def __bool__(self):
        return bool(self.lines)

    def range(self):
        if len(self.lines) > 1:
            first, *_, last = self.lines
            return "{0}..{1}".format(first.id, last.id)
        else:
            first = self.lines[0]
            return first.id


class Line:

    c = 0

    def __init__(self, name, dipls, extid=""):
        Line.c += 1
        self._id = "l{0}".format(Line.c)
        self.id = extid if extid else ""
        self.name = name
        self.dipls = dipls

    def __bool__(self):
        return bool(self.dipls)

    # keep?
    def loc(self):
        pass

    def range(self):
        if len(self.dipls) > 1:
            first, *middle, last = self.dipls
            # if first dipl token was merged into last line, then it won't have
            # an ID in that case, just use second token ID for range
            if middle:
                return "{0}..{1}".format(first.id
                                         if hasattr(first, "id")
                                         else middle[0].id,
                                         last.id)
            else:
                return "{0}..{1}".format(first.id, last.id)

        else:
            first = self.dipls[0]
            return first.id


class CoraToken:

    c = 0

    def __init__(self, trans, tok_dipls, tok_annos, extid=""):
        CoraToken.c += 1
        self._id = "t{0}".format(CoraToken.c)
        self.id = extid if extid else ""
        self.trans = trans
        self.tok_dipls = tok_dipls
        self.tok_annos = tok_annos

    def __str__(self):
        return str(self.trans)

    def merge_token(self, tok, join_dipls=False, join_mods=False):
        self.trans += tok.trans

        # dipls are never merged directly in order to preserve layout info
        self.tok_dipls.extend(tok.tok_dipls)

        if join_mods:
            if tok.tok_annos:
                first, *rest = tok.tok_annos
                self.tok_annos[-1].merge(first)
                self.tok_annos.extend(rest)
            else:
                pass  # happens when token-to-merge is unintelligible
        else:
            self.tok_annos.extend(tok.tok_annos)


class TokDipl:

    c = 0

    def __init__(self, trans, extid=""):
        TokDipl.c += 1
        self._id = "d{0}".format(TokDipl.c)
        self.id = extid if extid else ""
        self.trans = trans

    def __str__(self):
        return str(self.trans)

    def __eq__(self, other):
        return (self.id == other.id) and (self.trans == other.trans)


class TokAnno:

    ## TODO: move to coraxml_exporter, dialect="rem"
    # annos_order = ["norm", "token_type", "lemma", "lemma_gen", "lemma_idmwb",
    #                "pos", "pos_gen", "infl", "inflClass", "inflClass_gen",
    #                "punc", "link"]
    c = 0

    def __init__(self, trans, extid="", tags=None, flags=None, checked=False):
        TokAnno.c += 1
        self._id = "a{0}".format(TokAnno.c)
        self.id = extid if extid else ""
        self.trans = trans
        self.tags = tags if tags else dict()
        self.flags = flags if flags else set()
        self.checked = checked

    def __str__(self):
        return str(self.trans)

    def __eq__(self, other):
        return (self.id == other.id) and (self.trans == other.trans)

    def merge(self, other):
        self.trans.parse += other.trans.parse


class CoraComment:

    def __init__(self, _type, content):
        self.type = _type
        self.content = content

    def __str__(self):
        return "+{0} {1} @{0}".format(self.type,
                                      " ".join(self.content))


class ShiftTag:

    def __init__(self, _type, tokens):
        self.type = _type
        self.tokens = tokens

    def range(self):
        if len(self.elements) > 1:
            first, *_, last = self.elements
            return "{0}..{1}".format(first.id, last.id)
        elif len(self.elements) == 1:
            first = self.elements[0]
            return first.id
        else:
            return ""

    def tag(self):
        return {"F": "fm",
                "L": "lat",
                "R": "rub",
                "Ü": "title",
                "M": "marg",
                "Q": "question"}.get(self.type, "shifttag")
