
class BaseTrans:

    def __init__(self, myparse):
        self.parse = myparse

    def __len__(self):
        return len(self.parse)

    def __eq__(self, other):
        return self.parse == other.parse

    def __repr__(self):
        return str(self.parse)

    def __str__(self):
        return self.trans()

    def __iadd__(self, other):
        return self.__class__(self.parse + other.parse)

    def trans(self):
        return "".join(c.get("trans") for c in self.parse)

    def keep(self, *types):
        return self.__class__([c for c in self.parse if c["type"] in types])

    def has(self, *types):
        return any(c["type"] in types for c in self.parse)
        
    def delete(self, *types):
        return self.__class__([c for c in self.parse if c["type"] not in types])


class AnnoTrans(BaseTrans):

    def __init__(self, myparse):
        super().__init__(myparse)

    def utf(self):
        return "".join(c.get("anno_utf") for c in self.parse)

    def simple(self):
        return "".join(c.get("anno_simple") for c in self.parse)


class DiplTrans(BaseTrans):

    def __init__(self, myparse, subtoken=None):
        super().__init__(myparse)
        self.subtoken_annos = subtoken

    def utf(self):
        return "".join(c.get("dipl_utf") for c in self.parse)

    def get_subtoken_tree(self):
        # TODO
        pass


class Trans(BaseTrans):

    def __init__(self, myparse, anno_splits=None, dipl_splits=None, subtoken=None):
        super().__init__(myparse)
        
        self.dipl_tok_bounds = dipl_splits if dipl_splits else []
        self.anno_tok_bounds = anno_splits if anno_splits else []

        self.subtoken_annos = subtoken

    # TODO: these methods should also close the open brackets
    #  that result from tokenization (since all tokens are 
    #  validated on parsing, we can assume that all open 
    #  brackets are open due to tokenization and are not
    #  transcription errors)
    def tokenize_anno(self):
        output_tokens = list()
        stack = list()
        for i, c in enumerate(self.parse):
            if i + 1 in self.anno_tok_bounds:
                output_tokens.append(AnnoTrans(stack))
                stack = list()
            stack.append(c)
        output_tokens.append(AnnoTrans(stack))
        return output_tokens

    def tokenize_dipl(self):
        output_tokens = list()
        stack = list()
        for i, c in enumerate(self.parse):
            if i + 1 in self.dipl_tok_bounds:
                output_tokens.append(DiplTrans(stack, subtoken=self.subtoken_annos))
                stack = list()
            stack.append(c)
        output_tokens.append(DiplTrans(stack))
        return output_tokens

    def get_parse_with_tokenization(self):

        # create copy
        aligned_parse = list(self.parse)
        # add token boundaries to parse
        for bound_position in self.dipl_tok_bounds:
            aligned_parse[bound_position]['dipl_boundary'] = True
        for bound_position in self.anno_tok_bounds:
            aligned_parse[bound_position]['anno_boundary'] = True
        return aligned_parse


class SubtokenAnno:

    def __init__(self, mytype, start_index, end_index):
        self.type = mytype
        self.start = start_index
        self.end = end_index

    def __str__(self):
        return "<'" + self.type + "' range=(" + self.start + ", " + self.end + ")>"

    def __repr__(self):
        return str(self)


class Document:

    def __init__(self, sigle, name, header, pages, tokens, shifttags=None, header_string=None, annospans=None):
        self.sigle = sigle
        self.name = name
        self.header = header
        self.header_string = header_string

        self.pages = pages
        self.tokens = tokens
        self.shifttags = shifttags if shifttags else []
        self.annospans = annospans if annospans else []

    def __bool__(self):
        return bool(self.pages and self.tokens)


class Page:

    c = 0

    def __init__(self, name, side, columns, extid=""):
        Page.c += 1
        self._id = "p{0}".format(Page.c)
        self.id = extid if extid else self._id
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

    def __init__(self, lines, name="", extid=""):
        Column.c += 1
        self._id = "c{0}".format(Column.c)
        self.id = extid if extid else self._id
        self.name = name
        self.lines = lines

    def __bool__(self):
        return bool(self.lines)

    def range(self):
        if len(self.lines) > 1:
            first, *_, last = self.lines
            return "{0}..{1}".format(first.id, last.id)
        elif len(self.lines) == 1:
            first = self.lines[0]
            return first.id
        else:
            return ""


class Line:

    c = 0

    def __init__(self, name, dipls, extid=""):
        Line.c += 1
        self._id = "l{0}".format(Line.c)
        self.id = extid if extid else self._id
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
        self.id = extid if extid else self._id
        self.trans = trans
        self.tok_dipls = tok_dipls
        self.tok_annos = tok_annos

    def __str__(self):
        return str(self.trans)

    def __eq__(self, other):
        return (self.id == other.id and
                self.trans == other.trans and
                self.tok_dipls == other.tok_dipls and
                self.tok_annos == other.tok_annos)

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
        self.id = extid if extid else self._id
        self.trans = trans

    def __str__(self):
        return str(self.trans)

    def __eq__(self, other):
        return (self.id == other.id) and (self.trans == other.trans)


class AnnotatableElement:

    def __init__(self, tags=None, flags=None):

        self.tags = tags if tags else dict()
        self.flags = flags if flags else set()


class TokAnno(AnnotatableElement):

    ## TODO: move to coraxml_exporter, dialect="rem"
    # annos_order = ["norm", "token_type", "lemma", "lemma_gen", "lemma_idmwb",
    #                "pos", "pos_gen", "infl", "inflClass", "inflClass_gen",
    #                "punc", "link"]
    c = 0

    def __init__(self, trans, extid="", tags=None, flags=None, checked=False):
        TokAnno.c += 1
        self._id = "a{0}".format(TokAnno.c)
        self.id = extid if extid else self._id
        self.trans = trans
        self.checked = checked
        super().__init__(tags=tags, flags=flags)

    def __str__(self):
        return str(self.trans)

    def __eq__(self, other):
        return (self.id == other.id and
                self.trans == other.trans and
                self.tags == other.tags and
                self.flags == other.flags and
                self.checked == other.checked
        )

    def merge(self, other):
        self.trans.parse += other.trans.parse


class AnnoSpan(AnnotatableElement):

    def __init__(self, annos, tags=None, flags=None):
        self.annos = annos
        super().__init__(tags=tags, flags=flags)


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
        if len(self.tokens) > 1:
            first, *_, last = self.tokens
            return "{0}..{1}".format(first.id, last.id)
        elif len(self.tokens) == 1:
            first = self.tokens[0]
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
