import logging
from collections import defaultdict

import regex
import lark

from coraxml_utils.character import *
from coraxml_utils.coralib import Trans, DiplTrans, AnnoTrans, SubtokenAnno

logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger()

MEDIUS = "\u00b7"
ELEVATUS = "\uf161"
PARAGRAPHUS = "\uf1e1"
BULLET = "\u2219"  # used strangely often in REM
ALPHA = "abcdefghijklmnopqrstuvwxyz"


class ParseError(Exception):
    def __init__(self, msg):
        self.message = msg


class BaseParser:
    def __init__(self):
        self.token_re = regex.compile(
            r"({0})".format("|".join(self.re_parts)), flags=regex.VERBOSE
        )

    def validate(self, obj, output_type="trans", span_errors=None):
        # TODO at the moment, this function will only report one error
        #      at a time instead of all errors in token

        if span_errors:
            # concatenate messages meaningfully
            span_err_msg = ", ".join(span_errors)
            # raise ParseError
            raise ParseError(span_err_msg)

        # remove all valid characters, now everything that remains
        # is an error. also remove \&1-9 "variables zeichen"
        # which gets simplified to {1-9}
        # and %[A-Z] which is code for a superscript capital
        # note that superscript capitals are unchanged because unicode does
        # not support superscripting of arbitrary characters
        if any(x is None for x in obj.parse):
            for x in obj.parse:
                print(len(obj.parse))
                print(x.__class__.__name__, x.string, sep="\t")

        last_char = None
        for c in obj.parse:
            if (
                isinstance(last_char, Joiner)
                and not isinstance(c, LineBreak)
                and output_type != "anno"
            ):
                if (
                    not isinstance(
                        last_char, Hyphen
                    )  # allows = mid-line as required by legacy tests
                ) and (
                    not isinstance(
                        last_char, UniverbNewline
                    )  # allows (=) mid-line as appearing in Anselm in REF - change?
                ):
                    raise ParseError("%s not at line end" % last_char.string)
            elif isinstance(last_char, MultiverbSpace) and isinstance(c, Hyphen):
                raise ParseError(
                    "Transcription contains erroneous tokenization symbol: "
                    + obj.trans()
                )
            elif isinstance(last_char, Univerbation) and isinstance(c, Multiverbation):
                raise ParseError(
                    "Contradictory annotations in transcription: " + obj.trans()
                )
            elif isinstance(last_char, Multiverbation) and isinstance(c, Univerbation):
                raise ParseError(
                    "Contradictory annotations in transcription: " + obj.trans()
                )
            last_char = c

        test_string = "".join(
            c.anno_simple for c in obj.parse if not isinstance(c, MetaChar)
        )
        if isinstance(self, RediParser):
            test_string = regex.sub(r"{[1-9][0-9]?}", "", test_string)
        else:
            test_string = regex.sub(r"{[1-9]}", "", test_string)
        test_string = regex.sub(r"%[A-Z]", "", test_string)
        test_string = regex.sub(self.ESCAPE_CHAR, "", test_string)
        invalid_chars = set(test_string) - self.allowed

        if invalid_chars:
            raise ParseError(
                "Transcription "
                + obj.trans()
                + " contains invalid characters: "
                + str(sorted(invalid_chars))
            )


class PlainParser(BaseParser):
    def __init__(self):
        self.ATOMIC_ILLEGIBLE = ""
        self.ILLEGIBLE_REPLACEMENT = "[...]"
        self.missing_br_open = {}

        spc_re = r"(?P<spc> [ \t]+ ) | (?P<newline> \n )"
        word_re = r"(?P<w> . )"
        self.re_parts = [spc_re, word_re]

        # LIST OF ALLOWED CHARACTERS FOR validity check
        self.allowed = set(ALPHA)
        self.allowed.update(ALPHA.upper())
        self.allowed.update(r'-",.:;\/!?1234567890ßäöüÄÖÜ ')
        self.allowed.update("'()[]{}")

        self.ESCAPE_CHAR = regex.compile(
            r"&([^" + regex.escape("".join(self.allowed)) + r"])"
        )

        self.dipl_utf_opts = None
        self.anno_utf_opts = None
        self.anno_simple_opts = None

        super().__init__()

    def validate(self, obj, output_type="trans"):
        pass

    def tokenize(self, some_parse, split_init_punc=True):

        some_parse[-1].dipl_bound = True
        some_parse[-1].anno_bound = True

        return some_parse

    def parse(self, intoken, output_type="trans"):
        """
        output_type: {"trans", "dipl", "anno"}
        """
        myparse = list()
        subtoken_spans = list()  # list of SubtokenAnnos
        new_char = None

        for match in self.token_re.scanner(intoken):
            for key, val in match.groupdict().items():
                if val:
                    if key == "w":
                        new_char = TextChar(
                            val, dipl_utf=val, anno_utf=val, anno_simple=val
                        )
                    elif key == "newline":
                        new_char = LineBreak(val)
                    else:
                        raise ParseError("Something went wrong!")

                    myparse.append(new_char)

        if output_type.startswith("dipl"):
            result = DiplTrans(myparse, subtoken=subtoken_spans)
        elif output_type.startswith("anno"):
            result = AnnoTrans(myparse)
        else:
            myparse = self.tokenize(myparse)
            result = Trans(myparse, subtoken=subtoken_spans)
        self.validate(result, output_type)  # throws ParseError
        return result


class RexParser(BaseParser):
    def __init__(self):
        self.ILLEGIBLE_REPLACEMENT = "[...]"
        self.missing_br_open = {"["}

        alpha = r"[A-Za-zÄÖÜäöüß$]"
        punc = r"[.;!?:,]"
        no_pq = r'(?![.;!?:,"«»])'

        # char types
        abbr_re = r"(?P<abbr> %?\.[a-zA-Z]{1,4}%?\. | e%\.e%\. | %[A-Z] ) "
        spc_re = r"(?P<spc> [ \t]+ ) | (?P<newline> \n )"
        word_re = r"(?P<w>  \\ . | . )"
        uni_re = "|".join(
            "(?P<uni{0}>".format(i) + x + ")"
            for i, (x, _, _) in enumerate(replacements)
            if x
        )
        period_re = r"(?P<period> \. )"
        punc_re = r"(?P<p> %\. | / | " + punc + ")"
        majuscule_re = (
            r"(?P<maj> [*÷] [{(<] (?P<majc>"
            + alpha
            + r"{,3}) [*÷] (?P<majs>\d*) [})>] )"
        )
        hyphen_re = r"(?P<hyphen> = )"
        parens_re = r"(?P<pareno> &\( ) | (?P<parenc> &\) )"

        # annotations
        foreign_re = r"(?P<for> \*f )"
        preedit_re = (
            r"(?P<pe> \("
            + punc
            + r"\) | ,,\) | ,,\("
            + no_pq
            + r"| ,\) | ,\("
            + no_pq
            + r" | ,, )"
        )
        ptk_marker_re = r"(?P<ptk> \*1 | \*2 )"
        quote_re = r'(?P<q> \(["«»]\) )'
        tokenization_re = (
            r"(?P<ul> \(=\) ) | (?P<ml> =\| ) | (?P<ms> \|+ ) | (?P<us> \# )"
        )

        # sequence annotations
        strk_re = r"(?P<strko> \*\[ ) | (?P<strkc> \*\] )"
        hard_to_read_re = r"(?P<reado> < ) | (?P<readc> > )"
        edition_re = r"(?P<edito> \[ ) | (?P<editc> \] )"
        editor_completed_re = r"(?P<complo> \[\[ ) | (?P<complc> \]\] )"
        # lacuna_re = r'(?P<gapo> << ) | (?P<gapc> >> )'
        lacuna_re = r"(?P<gap> <<\.\.\.>> )"

        # specifies which regexes are to be applied, and in what order
        # order longer patterns before shorter ones!!
        self.re_parts = [
            spc_re,
            abbr_re,
            majuscule_re,
            tokenization_re,
            parens_re,
            lacuna_re,
            editor_completed_re,
            strk_re,
            hard_to_read_re,
            edition_re,
            ptk_marker_re,
            quote_re,
            preedit_re,
            uni_re,
            hyphen_re,
            period_re,
            punc_re,
            foreign_re,
            word_re,
        ]

        # LIST OF ALLOWED CHARACTERS FOR validity check
        self.allowed = set(ALPHA)
        self.allowed.update(ALPHA.upper())
        self.allowed.update(r'-",.:;\/!?1234567890ßäöüÄÖÜ\n')
        # for r-kuerzung
        self.allowed.update("'")

        self.ESCAPE_CHAR = regex.compile(
            r"&([^" + regex.escape("".join(self.allowed)) + r"])"
        )

        self.init_parser()

        super().__init__()

    def init_parser(self):
        pass

    def parse(self, intoken, output_type="trans"):
        """
        output_type: {"trans", "dipl", "anno"}
        """
        myparse = list()
        subtoken_spans = list()  # list of SubtokenAnnos
        open_spans = defaultdict(list)  # {type, [start1, start2, ...]}
        intoken_span_errs = (
            list()
        )  # span-related errors will be passed to validation fn

        for match in self.token_re.scanner(intoken):
            new_char = None
            for key, val in match.groupdict().items():
                if val:
                    if key == "spc":
                        # disallow brackets that span multiple tokens
                        if any(val for key, val in open_spans.items()):
                            intoken_span_errs.append(
                                "unclosed bracket at end of token: '{0}'".format(
                                    intoken
                                )
                            )
                        new_char = Whitespace(val)
                    elif key == "newline":
                        # disallow brackets that span multiple tokens
                        if any(val for key, val in open_spans.items()):
                            intoken_span_errs.append(
                                "unclosed bracket at end of line: '{0}'".format(intoken)
                            )
                        new_char = LineBreak(val)

                    elif key == "strko":
                        new_char = Strikethrough(val, opening=True)
                        open_spans[Strikethrough].append(match.start())
                    elif key == "strkc":
                        # TODO: strikethrough may span multiple tokens?
                        try:
                            closing = open_spans[Strikethrough].pop()
                            subtoken_spans.append(
                                SubtokenAnno(Strikethrough, closing, match.end())
                            )
                            new_char = Strikethrough(val, opening=False)
                        except IndexError:
                            intoken_span_errs.append(
                                "closing bracket '{0}' not opened".format(val)
                            )

                    elif key == "reado":
                        open_spans[Recognizable].append(match.start())
                        new_char = Recognizable(val, opening=True)
                    elif key == "readc":
                        try:
                            closing = open_spans[Recognizable].pop()
                            subtoken_spans.append(
                                SubtokenAnno(Recognizable, closing, match.end())
                            )
                            new_char = Recognizable(val, opening=False)
                        except IndexError:
                            intoken_span_errs.append(
                                "closing bracket '{0}' not opened".format(val)
                            )

                    elif key == "edito":
                        open_spans[FromEdition].append(match.start())
                        new_char = FromEdition(
                            val,
                            opening=True,
                            dipl_utf=self.ILLEGIBLE_REPLACEMENT,
                            anno_utf=self.ILLEGIBLE_REPLACEMENT,
                        )
                    elif key == "complo":
                        open_spans[EditorCompleted].append(match.start())
                        new_char = EditorCompleted(
                            val,
                            opening=True,
                            dipl_utf=self.ILLEGIBLE_REPLACEMENT,
                            anno_utf=self.ILLEGIBLE_REPLACEMENT,
                        )
                    elif key == "gap":
                        new_char = Lacuna(
                            val,
                            dipl_utf=self.ILLEGIBLE_REPLACEMENT,
                            anno_utf=self.ILLEGIBLE_REPLACEMENT,
                        )
                    elif key in {"editc", "complc"}:
                        try:
                            # TODO update strings TODO ????
                            # openbr = flip_bracket(val)
                            if key == "editc":
                                closing = open_spans[FromEdition].pop()
                                subtoken_spans.append(
                                    SubtokenAnno(FromEdition, closing, match.end())
                                )
                                new_char = FromEdition(val, opening=False)
                            elif key == "complc":
                                closing = open_spans[EditorCompleted].pop()
                                subtoken_spans.append(
                                    SubtokenAnno(EditorCompleted, closing, match.end())
                                )
                                new_char = EditorCompleted(val, opening=False)
                        except IndexError:
                            intoken_span_errs.append(
                                "closing bracket '{0}' not opened".format(val)
                            )

                    elif key == "pareno":
                        # TODO figure out what should be done here
                        new_char = Parenthesis(
                            val, dipl_utf="(", anno_utf="(", anno_simple="("
                        )
                    elif key == "parenc":
                        new_char = Parenthesis(
                            val,
                            dipl_utf=")",
                            anno_utf=")",
                            anno_simple=")",
                            opening=False,
                        )

                    elif key == "hyphen":
                        new_char = Hyphen(val, dipl_utf=val)
                    elif key == "pe":
                        new_char = SentBound(val, anno_utf=val, anno_simple=val)
                    elif key == "q":
                        new_char = QuotationMark(val, anno_utf=val, anno_simple=val)
                    elif key == "ptk":
                        new_char = ParticleLink(val)
                    elif key == "for":
                        new_char = ForeignMarker(val)

                    elif key == "ul":
                        new_char = UniverbNewline(val)
                    elif key == "ml":
                        new_char = MultiverbNewline(val, dipl_utf="=")
                    elif key == "us":
                        new_char = UniverbSpace(val)
                    elif key == "ms":
                        new_char = MultiverbSpace(val)

                    else:
                        if key.startswith("uni"):
                            _, utfchar, simplechar = replacements[int(key[3:])]
                            ##  TODO: regex should make this distinction
                            # special case for punc w/ utf conversions
                            if val != "\\." and "." in val or "·" in val:
                                new_char = Punct(
                                    val,
                                    dipl_utf=utfchar,
                                    anno_utf=utfchar,
                                    anno_simple=simplechar,
                                )
                            elif "*C" in val:
                                new_char = Punct(
                                    val,
                                    dipl_utf=utfchar,
                                    anno_utf=utfchar,
                                    anno_simple=simplechar,
                                )
                            else:
                                new_char = TextChar(
                                    val,
                                    dipl_utf=utfchar,
                                    anno_utf=utfchar,
                                    anno_simple=simplechar,
                                )
                        elif key == "maj":
                            maj_letter = match.group("majc")
                            mysize = match.group("majs")
                            new_char = Majuscule(
                                val,
                                size=mysize,
                                dipl_utf=maj_letter.replace("$", "\u017F"),
                                anno_utf=maj_letter.replace("$", "\u017F"),
                                anno_simple=maj_letter.replace("$", "s"),
                            )
                        else:
                            if key == "w":
                                new_char = TextChar(
                                    val, dipl_utf=val, anno_utf=val, anno_simple=val
                                )
                            elif key == "abbr":
                                anno_val = regex.sub(
                                    r"%?\.([A-Za-zÄÖÜäöüß$]+)%?\.",
                                    "\u00B7\\1\u00B7",
                                    val,
                                )
                                simple_val = regex.sub(
                                    r"%?\.([A-Za-zÄÖÜäöüß$]+)%?\.", r".\1.", val
                                )

                                new_char = TextChar(
                                    val,
                                    dipl_utf=val,
                                    anno_utf=anno_val,
                                    anno_simple=simple_val,
                                )
                            elif key == "p":
                                new_char = Punct(
                                    val, dipl_utf=val, anno_utf=val, anno_simple=val
                                )
                            elif key == "period":
                                if open_spans.get(EditorCompleted):
                                    new_char = IllegibleChar(
                                        val, dipl_utf=val, anno_utf=val, anno_simple=val
                                    )
                                else:
                                    new_char = Punct(
                                        val, dipl_utf=val, anno_utf=val, anno_simple=val
                                    )
                            elif key in {"majc", "majs"}:
                                # skip (will be handled by "maj" case)
                                continue
                            else:
                                raise ParseError(
                                    "Unknown key: '{0}' in token '{1}'".format(
                                        key, intoken
                                    )
                                )

                        # process open spans (omit illegible chars as required)
                        if open_spans.get(FromEdition) or open_spans.get(
                            EditorCompleted
                        ):
                            new_char.dipl_utf = ""
                            new_char.anno_utf = ""
                            new_char.illegible = True
                        elif open_spans.get(Strikethrough):
                            new_char.anno_utf = ""
                            new_char.anno_simple = ""
                            new_char.strikethrough = True

                    if new_char is None:
                        raise RuntimeError(
                            "Unexpected parse error. This should never happen! {0}, {1}".format(
                                key, intoken
                            )
                        )
                    else:
                        myparse.append(new_char)
                    break  # <- exactly one char should result from each match

            if new_char is None:
                logging.warning("Empty char results from " + intoken)

        if any(val for key, val in open_spans.items()):
            intoken_span_errs.append("unclosed bracket '{0}'".format(val))

        if output_type.startswith("dipl"):
            result = DiplTrans(myparse, subtoken=subtoken_spans)
        elif output_type.startswith("anno"):
            result = AnnoTrans(myparse)
        else:
            myparse = self.tokenize(myparse)
            result = Trans(myparse, subtoken=subtoken_spans)
            try:
                # NB: only validate whole tokens
                #  (in general dipl and mod trans are only parsed
                #   once the whole token has been parsed anyway,
                #   so just validating the whole thing should be enough)
                self.validate(
                    result, output_type, span_errors=intoken_span_errs
                )  # throws ParseError
            except ParseError as e:
                raise ParseError(
                    "The token '{0}' could not be parsed:\n\t{1}".format(
                        intoken, e.message
                    )
                )
        return result

    def tokenize(self, some_parse):

        padded_parse = [Whitespace("")] + some_parse + [Whitespace("")]

        for i in range(1, len(padded_parse) - 1):
            last_char, this_char, next_char = padded_parse[i - 1 : i + 2]

            # if hyphens are dipl bounds, these should be too
            #   (also present in handschrift)
            if isinstance(
                last_char, (UniverbSpace, UniverbNewline, Hyphen, MultiverbNewline)
            ) and not isinstance(this_char, Bracket):
                this_char.dipl_bound = True

            # special cases such as w[[a=]]ren (boundary after brackets)
            elif (
                isinstance(
                    last_char, (UniverbSpace, UniverbNewline, Hyphen, MultiverbNewline)
                )
                and isinstance(this_char, Bracket)
                and not this_char.opening
            ):
                next_char.dipl_bound = True

            # special cases such as <wa>=<ren> (*opening* boundary after brackets)
            elif (
                isinstance(
                    last_char, (UniverbSpace, UniverbNewline, Hyphen, MultiverbNewline)
                )
                and isinstance(this_char, Bracket)
                and this_char.opening
            ):
                this_char.dipl_bound = True

            # word split "foo|bar"
            if isinstance(last_char, (MultiverbSpace, MultiverbNewline)):
                this_char.anno_bound = True

            # other initial punctuation
            if (
                isinstance(last_char, Whitespace)
                and not isinstance(last_char, LineBreak)
                and isinstance(this_char, Punct)
                and not isinstance(next_char, Punct)
            ):
                next_char.anno_bound = True

            # final punctuation  "foo%." (NOT "f%.oo")
            if (
                (
                    isinstance(last_char, TextChar)
                    or (isinstance(last_char, Bracket) and not last_char.opening)
                )
                and isinstance(this_char, Punct)
                and not (
                    isinstance(next_char, TextChar)
                    or isinstance(next_char, Joiner)
                    or isinstance(next_char, UniverbSpace)
                )
            ):
                this_char.anno_bound = True

            # separate punct from punct (if different)
            if (
                isinstance(last_char, Punct)
                and isinstance(this_char, Punct)
                and last_char.string != this_char.string
            ):
                this_char.anno_bound = True

            # separate punct after ptk
            if isinstance(last_char, ParticleLink) and isinstance(this_char, Punct):
                this_char.anno_bound = True

            # seperate punct in klammern
            if (
                isinstance(last_char, Bracket)
                and isinstance(this_char, Punct)
                and isinstance(next_char, Bracket)
            ):
                last_char.anno_bound = True

            # preeditionszeichen
            #  (with special handling of initial quotation marks)
            if isinstance(last_char, (Whitespace, MultiverbSpace)) and isinstance(
                this_char, QuotationMark
            ):
                next_char.anno_bound = True
            elif isinstance(this_char, SentBound) and not isinstance(
                next_char, (MultiverbSpace, MultiverbNewline)
            ):
                this_char.anno_bound = True

        # CoraToken bounds
        if not (some_parse[-1].anno_bound or some_parse[-1].dipl_bound):
            some_parse[-1].token_bound = True

        return some_parse


#  TODO: finish converting to RexParser derivative
class RemParser(RexParser):
    def init_parser(self):
        self.ATOMIC_ILLEGIBLE = "<<...>>"
        self.ILLEGIBLE_REPLACEMENT = "[...]"
        self.missing_br_open = {"["}

        # degree sign for foreign-language text (won't be removed)
        self.allowed.update("°")

        quote_re = r'(?P<q> " | « | » )'
        parens_re = r"(?P<pareno> \( ) | (?P<parenc> \) )"
        tokenization_re = (
            r"(?P<ul> \(=\) ) | (?P<ml> =\| ) | (?P<ms> \|+ ) | (?P<us> \# ) | "
            + r" (?P<uc> ~\(=\) ) | (?P<mc> ~| ) | (?P<conj> ~ ) "
        )

        # self.ESCAPE_CHAR = re.compile(r"&([^" + re.escape("".join(self.allowed)) + r"])")

        # super().__init__()

        # # in REM, [[...]] is often used (apparently erroneously) to
        # # denote missing letters or lines, so here I replace such
        # # instances with the correct abbr, [...]
        # new_parse = list()
        # for c in self.parse:
        #     if c["type"] == "abbr" and c["char"] == "[[...]]":
        #         c["char"] = "[...]"
        #     new_parse.append(c)
        # self.parse = new_parse


class RefParser(RexParser):
    def init_parser(self):
        self.allowed.update("()«»")


class AnselmParser(RexParser):
    pass


class RediParser(RexParser):
    pass


## get all subclass
def __get_all_subclasses(cls):
    return cls.__subclasses__() + [
        g for s in cls.__subclasses__() for g in __get_all_subclasses(s)
    ]


def __parse_tree_transformer_init(self, char_mapping=None):
    self._create_char = char_mapping
    if self._create_char is None:
        self._create_char = lambda character: {
            "_trans": str(character),
            "dipl_utf": str(character),
            "anno_utf": str(character),
            "anno_simple": str(character),
        }


ParseTreeTransformer = lark.v_args(inline=True)(
    type(
        "ParseTreeTransformer",
        (lark.Transformer,),
        {
            **{
                "__doc__": """Transformer from flat parse trees to character classes

            Parse trees handled by this transformer should only have the root node 'start'
            with children containing tokens, with a name that is the (lowercased) name of the corresponding
            character class and the character as value. For brackets name_open and name_closed are expected.

            Args:
              char_mapping: A function that takes a character as input and returns its representations as dict.
                            Defaults to the character in all representations.
            """,
                "__init__": __parse_tree_transformer_init,
                "start": lambda self, *characters: characters,
            },
            ## add basic characters
            **{
                class_.__name__.lower(): lambda self, character, class_=class_: class_(
                    **self._create_char(character)
                )
                for class_ in __get_all_subclasses(Char)
                if not issubclass(class_, Bracket)
            },
            ## add whitspace
            **{
                class_.__name__.lower(): lambda self, character, class_=class_: class_(
                    self._create_char(character)["_trans"]
                )
                for class_ in [Whitespace] + __get_all_subclasses(Whitespace)
            },
            ## add brackets - open and close
            **{
                class_.__name__.lower()
                + "_open": lambda self, character, class_=class_: class_(
                    **self._create_char(character), opening=True
                )
                for class_ in __get_all_subclasses(Bracket)
            },
            **{
                class_.__name__.lower()
                + "_close": lambda self, character, class_=class_: class_(
                    **self._create_char(character), opening=False
                )
                for class_ in __get_all_subclasses(Bracket)
            },
        },
    )
)


class CFGParser:
    """Parse a text with a given context-free grammar.

    Args:
       grammar: either a file or a string containing the grammar in a format as expected by lark.
       transformer: lark.transformer that turns the parse tree into the parserd token.
                    Defaults to a transformer for flat parse trees.
    """

    def __init__(self, grammar, transformer=None):

        self.parser = lark.Lark(grammar, parser="lalr")
        ## handles ambiguities better, but is slow
        self.backup_parser = lark.Lark(grammar)
        self.transformer = transformer

        if self.transformer is None:
            self.transformer = ParseTreeTransformer()

    ## TODO how to support output_type? - different grammars? or use one grammar and filter illegal tokens for specific output types afterwards?
    def parse(self, intoken, output_type="trans"):

        try:
            tree = self.parser.parse(intoken)
        except Exception as e:
            try:
                tree = self.backup_parser.parse(intoken)
            except Exception as e:
                raise ParseError(intoken + " could not be parsed")
        parse = self.transformer.transform(tree)
        ## test if Tree elements are left
        if any([isinstance(x, lark.Tree) for x in parse]):
            # logger.debug(tree.pretty())
            print(tree.pretty())
            print(parse)
            raise ParseError(intoken + " parse could not be interpreted")

        ## TODO is this generic enough should this be changeable?
        ## add token boundaries
        add_dipl_bound = False
        add_anno_bound = False

        for char in parse:

            ## don't add breaks at closing brackets, whitepsace (including eol) or multiverbation character
            if (
                (not isinstance(char, Bracket) or char.opening)
                and not isinstance(char, Whitespace)
                and not isinstance(char, Multiverbation)
                and not isinstance(char, Univerbation)
            ):
                if add_dipl_bound:
                    char.dipl_bound = True
                    char.dipl_bound = True
                    add_dipl_bound = False
                if add_anno_bound:
                    char.anno_bound = True
                    add_anno_bound = False

            if isinstance(char, Multiverbation):
                add_anno_bound = True
            elif isinstance(char, Univerbation):
                add_dipl_bound = True
            elif isinstance(char, LineBreak):
                add_dipl_bound = True
            elif isinstance(char, Whitespace):
                add_dipl_bound = True

        return Trans(list(parse))


class ReNParser(CFGParser):
    def __init__(self):

        # note: this is a (rough) draft for a ReNParser using a context free grammar
        # the grammer does not parse full ReN transcriptions but Cora tokens
        # the parser expects whitespace between dipl tokens, SentBound's are not included
        # (they are represented as annotation in cora)
        ## this parser is not very strict - assumes validated transcriptions and creates parses

        # this parser's use case is to import the validated coraxml files from the ReN corpus
        # in order to convert them to other formats (e.g. tei)

        grammar = """

        start: lacuna | _token // a token is either a gap (lacuna), an editorial comment or a proper token

        !lacuna.2: "$Lücke$" // lacuna is a special editorial comment (higher priority)

        // a token consists of diplomatic tokens
        _token: _dipl_token_initial+
        _token_without_strikethrough: _dipl_token_initial_without_strikethrough+
        _dipl_token: ( _char | multiverbation | _bracket )+ // ( _char | _bracket )
        _dipl_token_without_strikethrough: ( _char | multiverbation | _bracket_without_strikethrough )+
        _dipl_token_initial: _dipl_token ( univerbation | multiverbation | hyphen )? (linebreak | whitespace)?
        _dipl_token_initial_without_strikethrough: _dipl_token_without_strikethrough ( univerbation | multiverbation | hyphen )? (linebreak | whitespace)?

        _char:  textchar | punct | hyphen | comment
        comment: /\$[^$]+\$/

        textchar: _letter | _special_letter | _digit
        _letter.2: /([A-Za-zØø]|\[…\])[ͣͤͥͦͧͮ̈]*/
        _special_letter: /[¶]/
        _digit: /[0-9]/
        //!illegiblechar.2: "[…]" // has priority over hard to read parts - is included into the normal letter category as it appears with diacritics
        !hyphen: "-" | "="
        !punct: "." | "," | "?" | ":" | "/" | "|" | "(" | ")"

        !univerbation: "#"
        !multiverbation: "§"

        !linebreak: "\\n"
        !whitespace: " "

        _bracket: _recognizable | _strikethrough | _abbr_expansion | _note | _addition | _correction | _continuation
        _bracket_without_strikethrough: _recognizable | _abbr_expansion | _note | _addition | _correction | _continuation
        _bracket_content: _token?
        _bracket_content_without_strikethrough: _token_without_strikethrough?
        _recognizable: recognizable_open _bracket_content recognizable_close
        !recognizable_open: "["
        !recognizable_close: "]"
        _strikethrough: strikethrough_open  _bracket_content_without_strikethrough strikethrough_close
        strikethrough_open: STRIKETHROUGH_OPEN_CHAR
        strikethrough_close: STRIKETHROUGH_CLOSE_CHAR
        STRIKETHROUGH_OPEN_CHAR: "ǂ"
        STRIKETHROUGH_CLOSE_CHAR: "ǂ"
        _abbr_expansion: expandedabbreviation_open  _bracket_content expandedabbreviation_close
        expandedabbreviation_open: /{[LRAEX]_/
        !expandedabbreviation_close: "}"
        _note: note_open _bracket_content note_close
        note_open: /\*[ILROUT]N_/
        !note_close: "*"
        _correction: correction_open _bracket_content correction_close
        correction_open: /\*[ILROUT]K_/
        !correction_close: "*"
        _addition: addition_open _bracket_content addition_close
        addition_open: /\*[ILROUT]E_/
        !addition_close: "*"
        _continuation:  continuation_open _bracket_content continuation_close
        !continuation_open: /\\\\F[UO]_/
        !continuation_close: "\\\\" // needs 4 backslashes to get one backslash
        """

        transformer = self.transformer = ParseTreeTransformer()
        super().__init__(grammar, transformer)

    def process_parse(self, parse, keep_deletions=False):

        in_deletion = False
        for idx, char in enumerate(parse):
            # remove deletions
            if isinstance(char, Strikethrough):
                in_deletion = char.opening
            if (
                isinstance(char, TokenBound)
                or isinstance(char, Bracket)
                or (not keep_deletions and in_deletion)
            ):
                char.dipl_utf = ""
                char.anno_utf = ""
                char.anno_simple = ""
            ## TODO the grammar currently labels IllegibleChar as normal TextChar - this is a fix
            elif isinstance(char, TextChar) and char.string == "[…]":
                parse.parse[idx] = IllegibleChar(
                    char.string, dipl_utf="…", anno_utf="…", anno_simple="…"
                )
                parse.parse[idx].anno_bound = char.anno_bound
                parse.parse[idx].dipl_bound = char.dipl_bound
                parse.parse[idx].token_bound = char.token_bound
                parse.parse[idx].line_break_after = char.line_break_after
            elif isinstance(char, Hyphen):
                char.anno_simple = ""

        return parse

    def parse(self, intoken, output_type="trans"):
        if output_type != "trans":
            raise NotImplementedError(
                "ReN parser currently only supports parsing whole CorA tokens."
            )
        else:
            parse = super().parse(intoken, output_type)
            import copy

            tmp_parse = copy.deepcopy(parse)
            self.process_parse(tmp_parse)
            ## if empty: return full transcription
            if not "".join([dipl.utf() for dipl in tmp_parse.tokenize_dipl()]):
                tmp_parse = self.process_parse(parse, True)

            return tmp_parse


## Assigns parsers to dialects
dialect_mapper = {
    None: PlainParser,
    "plain": PlainParser,
    "rem": RemParser,
    "ref": RefParser,
    "ren": ReNParser,
    "redi": RediParser,
    "anselm": AnselmParser,
}
