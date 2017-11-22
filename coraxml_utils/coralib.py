
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

    def __init__(self, name, side, columns):
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
    def __init__(self, name, lines):
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
    def __init__(self, name, dipls):
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

    def __init__(self, _id, trans, tok_dipls, tok_annos):
        self.id = _id
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

    def __init__(self, _id, trans):
        self.id = _id
        self.trans = trans

    def __str__(self):
        return str(self.trans)

    def __eq__(self, other):
        return (self.id == other.id) and (self.trans == other.trans)


class TokAnno:

    annos_order = ["norm", "token_type", "lemma", "lemma_gen", "lemma_idmwb",
                   "pos", "pos_gen", "infl", "inflClass", "inflClass_gen",
                   "punc", "link"]

    def __init__(self, _id, trans, tags=None, flags=None, checked=False):
        self.id = _id
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
