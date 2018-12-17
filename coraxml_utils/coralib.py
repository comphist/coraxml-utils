import abc

from collections import defaultdict

from coraxml_utils.character import Whitespace
from coraxml_utils.settings import DEFAULT_VAL

class BaseTrans:

    def __init__(self, myparse):
        self.parse = myparse

    def __len__(self):
        return len(self.parse)

    def __eq__(self, other):
        return self.parse == other.parse

    def __repr__(self):
        return str([str(x) for x in self.parse])

    def __str__(self):
        return self.trans()

    def __iadd__(self, other):
        return self.__class__(self.parse + other.parse)

    def trans(self):
        return "".join([c.string for c in self.parse if not isinstance(c, Whitespace)])

    def keep(self, t):
        return self.__class__([c for c in self.parse if isinstance(c, t)])

    def delete(self, t):
        return self.__class__([c for c in self.parse if not isinstance(c, t)])

    def has(self, *t):
        return any(isinstance(c, t) for c in self.parse)


class AnnoTrans(BaseTrans):

    def __init__(self, myparse):
        super().__init__(myparse)

    def utf(self):
        return "".join(c.anno_utf for c in self.parse)

    def simple(self):
        return "".join(c.anno_simple for c in self.parse)


class DiplTrans(BaseTrans):

    def __init__(self, myparse, subtoken=None):
        super().__init__(myparse)
        self.subtoken_annos = subtoken

    def utf(self):
        return "".join(c.dipl_utf for c in self.parse)

    def get_subtoken_tree(self):
        # TODO
        pass


class Trans(BaseTrans):

    def __init__(self, myparse, subtoken=None):
        super().__init__(myparse)

        self.subtoken_annos = subtoken

    def __iter__(self):
        return iter(self.parse)

    # TODO: these methods should also close the open brackets
    #  that result from tokenization (since all tokens are
    #  validated on parsing, we can assume that all open
    #  brackets are open due to tokenization and are not
    #  transcription errors)
    def tokenize_anno(self):
        output_tokens = list()

        ## if anno_utf is empty there are no anno tokens, e.g. in the case of deletions
        if not "".join(c.anno_utf for c in self.parse):
            return output_tokens

        stack = list()
        for c in self.parse:
            if c.anno_bound and not c.token_bound:
                output_tokens.append(AnnoTrans(stack).delete(Whitespace))
                stack = list()
            stack.append(c)
        if stack:
            output_tokens.append(AnnoTrans(stack).delete(Whitespace))
        return output_tokens

    def tokenize_dipl(self):
        output_tokens = list()
        stack = list()
        for c in self.parse:
            if c.dipl_bound and not c.token_bound:
                output_tokens.append(DiplTrans(stack, subtoken=self.subtoken_annos).delete(Whitespace))
                stack = list()
            stack.append(c)
        if stack:
            output_tokens.append(DiplTrans(stack).delete(Whitespace))
        return output_tokens

class SubtokenAnno:

    def __init__(self, mytype, start_index, end_index):
        self.type = mytype
        self.start = start_index
        self.end = end_index

    def __str__(self):
        return "<'" + self.type + "' range=(" + self.start + ", " + self.end + ")>"

    def __repr__(self):
        return str(self)

class IdentifiableObjectMixin:

    id_counter = defaultdict(int)

    def get_external_id(self):
        if self.id:
            return self.id
        else:
            return self.get_internal_id()

    def get_internal_id(self):

        return self._id

    def _set_id(self, t, extid=""):

        IdentifiableObjectMixin.id_counter[t] += 1
        self._id = "{}{}".format(t, IdentifiableObjectMixin.id_counter[t])

        ## TODO this is only to be compatible with existing code
        ## id should no longer be used to get the id -> use get_external_id
        self.id = extid if extid else self._id


class Document:

    def __init__(self, sigle, name, header, pages, tokens,
                 shifttags=None, header_string=None, annospans=None):
        self.sigle = sigle
        self.name = name
        self.header = header
        self.header_string = header_string

        self.pages = pages
        self.tokens = tokens
        self.shifttags = shifttags if shifttags else []
        self.annospans = annospans if annospans else []

        self._create_indices()

    ## TODO this should be called when document is changed
    def _create_indices(self):

        ## create index of line beginnings and endings
        self.index_line_beginnings = frozenset([line.dipls[0]._id
                                                for page in self.pages
                                                for column in page.columns
                                                for line in column.lines])

        self.index_line_endings = frozenset([line.dipls[-1]._id
                                                for page in self.pages
                                                for column in page.columns
                                                for line in column.lines])

        self.dipl_line_index = {
            dipl._id: line
            for page in self.pages
            for column in page.columns
            for line in column.lines
            for dipl in line.dipls
        }

    def __bool__(self):
        return bool(self.pages and self.tokens)

    def add_line(self, bibinfo):
        new_line = Line(bibinfo["line"], [])
        if self.pages:
            last_page = self.pages[-1]
            last_side = last_page.side
            last_col = last_page.columns[-1]

            if last_page.name != bibinfo["page"] or last_side != bibinfo["side"]:
                new_col = Column([new_line], name=bibinfo["col"])
                new_page = Page(bibinfo["page"], bibinfo["side"], [new_col])
                self.pages.append(new_page)
            elif last_col.name != bibinfo["col"]:
                new_col = Column([new_line], name=bibinfo["col"])
                last_page.columns.append(new_col)
            else:
                last_col.lines.append(new_line)
        else:
            new_col = Column([new_line], name=bibinfo["col"])
            new_page = Page(bibinfo["page"], bibinfo["side"], [new_col])
            self.pages.append(new_page)

        return new_line

    def is_beginning_of_line(self, tok_dipl):
        return tok_dipl._id in self.index_line_beginnings

    def is_end_of_line(self, tok_dipl):
        return tok_dipl._id in self.index_line_endings

    def get_line_for_dipl(self, tok_dipl):
        return self.dipl_line_index.get(tok_dipl._id, None)


class Page(IdentifiableObjectMixin):

    def __init__(self, name, side, columns, extid=""):
        self._set_id("p", extid)
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


class Column(IdentifiableObjectMixin):

    def __init__(self, lines, name="", extid=""):
        self._set_id("c", extid)
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


class Line(IdentifiableObjectMixin):

    def __init__(self, name, dipls, extid=""):
        self._set_id("l", extid)
        self.name = name
        self.dipls = dipls

    def __bool__(self):
        return bool(self.dipls)

    def __iter__(self):
        return iter(self.dipls)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "[" + ", ".join(str(d) for d in self.dipls) + "]"

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


class CoraToken(IdentifiableObjectMixin):

    def from_parse(parse):
        return CoraToken(parse,
                         [TokDipl(x) for x in parse.tokenize_dipl()],
                         [TokAnno(x) for x in parse.tokenize_anno()])

    def __init__(self, trans, tok_dipls, tok_annos, extid="", errors=None):
        self._set_id("t", extid)
        self.trans = trans
        self.tok_dipls = tok_dipls
        self.tok_annos = tok_annos
        self.errors = errors if errors else list()

    def __str__(self):
        return str(self.trans)

    def __eq__(self, other):
        return (self.id == other.id and
                self.trans == other.trans and
                self.tok_dipls == other.tok_dipls and
                self.tok_annos == other.tok_annos)

    # TODO: method is deprecated (due to new tokenizer module)
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

class TokDipl(IdentifiableObjectMixin):

    def __init__(self, trans: DiplTrans, extid=""):
        self._set_id("d", extid)
        self.trans = trans

    def __str__(self):
        return str(self.trans)

    def __eq__(self, other):
        return (self.id == other.id) and (self.trans == other.trans)


class AnnotatableElement:

    def __init__(self, tags=None, flags=None):

        self.tags = tags if tags else dict()
        self.flags = flags if flags else set()


    def append_annotation(self, tagname, tag, sep=' '):

        oldval = self.tags.get(tagname, DEFAULT_VAL)

        if oldval != DEFAULT_VAL:
            self.tags[tagname] = oldval + sep + tag
        else:
            self.tags[tagname] = tag



class TokAnno(AnnotatableElement, IdentifiableObjectMixin):

    ## TODO: move to coraxml_exporter, dialect="rem"
    # annos_order = ["norm", "token_type", "lemma", "lemma_gen", "lemma_idmwb",
    #                "pos", "pos_gen", "infl", "inflClass", "inflClass_gen",
    #                "punc", "link"]

    def __init__(self, trans, extid="", tags=None, flags=None, checked=False):
        self._set_id("a", extid)
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
        return "+{0} {1} @{0}".format(self.type, self.content)


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
                "Q": "question"}.get(self.type, self.type)
