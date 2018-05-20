
import regex
# import abc
import logging
logging.basicConfig(format='%(levelname)s: %(message)s')
logger = logging.getLogger()

from collections import defaultdict

from coraxml_utils.character import *
from coraxml_utils.coralib import Trans, DiplTrans, AnnoTrans, SubtokenAnno

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
        self.token_re = regex.compile(r"({0})".format("|".join(self.re_parts)), 
                                      flags=regex.VERBOSE)

    def validate(self, obj, output_type="trans"):
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
            if isinstance(last_char, Joiner) and not isinstance(c, LineBreak) and output_type!='anno':
                # allows = mid-line as required by legacy tests
                if not isinstance(last_char, Hyphen):
                    raise ParseError("%s not at line end" % last_char.string)
            elif isinstance(last_char, MultiverbSpace) and isinstance(c, Hyphen):
                raise ParseError("Transcription contains erroneous tokenization symbol: " + obj.trans())
            elif isinstance(last_char, Univerbation) and isinstance(c, Multiverbation):
                raise ParseError("Contradictory annotations in transcription: " + obj.trans())
            elif isinstance(last_char, Multiverbation) and isinstance(c, Univerbation):
                raise ParseError("Contradictory annotations in transcription: " + obj.trans())
            last_char = c

        test_string = "".join(c.anno_simple
                              for c in obj.parse
                              if not isinstance(c, MetaChar))
        if isinstance(self, RediParser):
            test_string = regex.sub(r"{[1-9][0-9]?}", "", test_string)
        else:
            test_string = regex.sub(r"{[1-9]}", "", test_string)
        test_string = regex.sub(r"%[A-Z]", "", test_string)
        test_string = regex.sub(self.ESCAPE_CHAR, "", test_string)
        invalid_chars = set(test_string) - self.allowed

        if invalid_chars:
            raise ParseError("Transcription " + obj.trans() + " contains invalid characters: " +
                             str(sorted(invalid_chars)))


class PlainParser(BaseParser):
    def __init__(self):
        self.ATOMIC_ILLEGIBLE = ""
        self.ILLEGIBLE_REPLACEMENT = "[...]"
        self.missing_br_open = {}

        spc_re = r"(?P<spc> [ \t]+ ) | (?P<newline> \n )"
        word_re = r'(?P<w> . )'
        self.re_parts = [spc_re, word_re]

        # LIST OF ALLOWED CHARACTERS FOR validity check
        self.allowed = set(ALPHA)
        self.allowed.update(ALPHA.upper())
        self.allowed.update('-",.:;\/!?1234567890ßäöüÄÖÜ ')
        self.allowed.update("'()[]{}")

        self.ESCAPE_CHAR = regex.compile(r"&([^" + regex.escape("".join(self.allowed)) + r"])")

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
        subtoken_spans = list() # list of SubtokenAnnos
        new_char = None

        for match in self.token_re.scanner(intoken):
            for key, val in match.groupdict().items():
                if val:
                    if key == "w":
                        new_char = TextChar(val, dipl_utf=val, anno_utf=val,
                                            anno_simple=val)
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
        self.missing_br_open = {'['}

        alpha = r"[A-Za-zÄÖÜäöüß$]"
        punc = r'[.;!?:,]'
        no_pq = r'(?![.;!?:,"«»])'

        # char types
        abbr_re = r"(?P<abbr> %?\.[a-zA-Z]{,2}%?\. | e%\.e%\. | %[A-Z] ) " 
        spc_re = r"(?P<spc> [ \t]+ ) | (?P<newline> \n )"
        word_re = r'(?P<w>  \\ . | . )'
        uni_re = "|".join("(?P<uni{0}>".format(i) + x + ")"
                            for i, (x, _, _) in enumerate(replacements) if x)
        period_re = r'(?P<period> \. )'
        punc_re = r'(?P<p> %\. | / | ' + punc +')'
        majuscule_re = r'(?P<maj> [*÷] [{(<] (?P<majc>' + alpha + r'{,3}) [*÷] (?P<majs>\d*) [})>] )'
        hyphen_re = r'(?P<hyphen> = )'
        parens_re = r'(?P<pareno> &\( ) | (?P<parenc> &\) )'

        # annotations
        foreign_re = r'(?P<for> \*f )'
        preedit_re = r'(?P<pe> \(' + punc + r'\) | ,,\) | ,,\(' + no_pq + r'| ,\) | ,\(' + no_pq + r' | ,, )'
        ptk_marker_re = r'(?P<ptk> \*1 | \*2 )'
        quote_re = r'(?P<q> \(["«»]\) )'
        tokenization_re = r'(?P<ul> \(=\) ) | (?P<ml> =\| ) | (?P<ms> \|+ ) | (?P<us> \# )'

        # sequence annotations
        strk_re = r'(?P<strko> \*\[ ) | (?P<strkc> \*\] )'
        hard_to_read_re = r'(?P<reado> < ) | (?P<readc> > )'
        edition_re = r'(?P<edito> \[ ) | (?P<editc> \] )'
        editor_completed_re = r'(?P<complo> \[\[ ) | (?P<complc> \]\] )'
        # lacuna_re = r'(?P<gapo> << ) | (?P<gapc> >> )'
        lacuna_re = r'(?P<gap> <<\.\.\.>> )'

        # specifies which regexes are to be applied, and in what order
        # order longer patterns before shorter ones!!
        self.re_parts = [spc_re, abbr_re, majuscule_re, tokenization_re, 
                         parens_re, lacuna_re,
                         editor_completed_re, strk_re, hard_to_read_re, edition_re,
                         ptk_marker_re, quote_re, preedit_re,
                         uni_re, hyphen_re, period_re, punc_re, foreign_re, word_re
                         ]


        # LIST OF ALLOWED CHARACTERS FOR validity check
        self.allowed = set(ALPHA)
        self.allowed.update(ALPHA.upper())
        self.allowed.update('-",.:;\/!?1234567890ßäöüÄÖÜ\n')
        # for r-kuerzung
        self.allowed.update("'")

        self.ESCAPE_CHAR = regex.compile(r"&([^" + regex.escape("".join(self.allowed)) + r"])")

        self.init_parser()

        super().__init__()

    def init_parser(self):
        pass

    def parse(self, intoken, output_type="trans"):
        """
        output_type: {"trans", "dipl", "anno"}
        """
        myparse = list()
        subtoken_spans = list() # list of SubtokenAnnos
        open_spans = defaultdict(list)    # {type, [start1, start2, ...]}

        for match in self.token_re.scanner(intoken):
            new_char = None
            for key, val in match.groupdict().items():
                if val:
                    # disallow brackets that span multiple tokens
                    if key == "spc":
                        if any(val for key, val in open_spans.items()):
                            raise ParseError("Unclosed bracket at end of token: " + intoken)
                        new_char = Whitespace(val) 
                    elif key == "newline":
                        if any(val for key, val in open_spans.items()):
                            raise ParseError("Unclosed bracket at end of line: " + intoken)
                        new_char = LineBreak(val)
                                
                    elif key == "strko":
                        new_char = Strikethrough(val, opening=True)
                        open_spans[Strikethrough].append(match.start())
                    elif key == "strkc":
                        # TODO: strikethrough may span multiple tokens?
                        try:
                            closing = open_spans[Strikethrough].pop()
                            subtoken_spans.append(SubtokenAnno(Strikethrough, closing, match.end()))
                            new_char = Strikethrough(val, opening=False)
                        except IndexError:
                            raise ParseError("Matching opening bracket missing: " + intoken)

                    elif key == "reado":
                        open_spans[Recognizable].append(match.start())
                        new_char = Recognizable(val, opening=True)
                    elif key == "readc":
                        try: 
                            closing = open_spans[Recognizable].pop()
                            subtoken_spans.append(SubtokenAnno(Recognizable, closing, match.end()))
                            new_char = Recognizable(val, opening=False)
                        except IndexError:
                            raise ParseError("Matching opening bracket missing: " + intoken)

                    elif key == "edito":
                        open_spans[FromEdition].append(match.start())
                        new_char = FromEdition(val, opening=True,
                                               dipl_utf=self.ILLEGIBLE_REPLACEMENT,
                                               anno_utf=self.ILLEGIBLE_REPLACEMENT)
                    elif key == "complo":
                        open_spans[EditorCompleted].append(match.start())
                        new_char = EditorCompleted(val, opening=True,
                                                   dipl_utf=self.ILLEGIBLE_REPLACEMENT,
                                                   anno_utf=self.ILLEGIBLE_REPLACEMENT)
                    elif key == "gap":
                        new_char = Lacuna(val,
                                           dipl_utf=self.ILLEGIBLE_REPLACEMENT,
                                           anno_utf=self.ILLEGIBLE_REPLACEMENT)
                    elif key in {"editc", "complc"}:
                        try:
                            # TODO update strings
                            # openbr = flip_bracket(val)
                            if key == "editc":
                                closing = open_spans[FromEdition].pop()
                                subtoken_spans.append(SubtokenAnno(FromEdition, closing, match.end())) 
                                new_char = FromEdition(val, opening=False)
                            elif key == "complc":
                                closing = open_spans[EditorCompleted].pop()
                                subtoken_spans.append(SubtokenAnno(EditorCompleted, closing, match.end())) 
                                new_char = EditorCompleted(val, opening=False)
                        except IndexError:
                            raise ParseError("Closing bracket is not opened: " + intoken)


                    elif key == "pareno":
                        # TODO figure out what should be done here
                        new_char = Parenthesis(val, dipl_utf="(", anno_utf="(",
                                               anno_simple="(")
                    elif key == "parenc":
                        new_char = Parenthesis(val, dipl_utf=")", anno_utf=")",
                                               anno_simple=")", opening=False)

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
                            # TODO: please revise, regex should make this distinction
                            # special case for punc w/ utf conversions
                            if val != "\\." and "." in val or "·" in val:
                                new_char = Punct(val, dipl_utf=utfchar, anno_utf=utfchar,
                                                 anno_simple=simplechar)
                            elif "*C" in val:
                                new_char = Punct(val, dipl_utf=utfchar, anno_utf=utfchar,
                                                 anno_simple=simplechar)
                            else:
                                new_char = TextChar(val, dipl_utf=utfchar, anno_utf=utfchar, 
                                                    anno_simple=simplechar)
                        elif key == "maj":
                            maj_letter = match.group("majc")
                            mysize = match.group("majs")
                            new_char = Majuscule(val, size=mysize,
                                                 dipl_utf=maj_letter.replace("$", "\u017F"),
                                                 anno_utf=maj_letter.replace("$", "\u017F"),
                                                 anno_simple=maj_letter.replace("$", "s"))
                        else:
                            if key == "w":
                                new_char = TextChar(val, dipl_utf=val, anno_utf=val,
                                                    anno_simple=val)
                            elif key == "abbr":
                                new_char = TextChar(val, dipl_utf=val, anno_utf=val,
                                                    anno_simple=val)
                            elif key == "p":
                                new_char = Punct(val, dipl_utf=val, anno_utf=val,
                                                 anno_simple=val)                    
                            elif key == "period":
                                if open_spans.get(EditorCompleted):
                                    new_char = IllegibleChar(val, dipl_utf=val, anno_utf=val,
                                                             anno_simple=val)
                                else:
                                    new_char = Punct(val, dipl_utf=val, anno_utf=val,
                                                     anno_simple=val)
                            elif key in {"majc", "majs"}:
                                # skip (will be handled by "maj" case)
                                continue
                            else:
                                raise ParseError("Unknown key: '{0}' in token '{1}'".format(key, intoken))

                        # process open spans (omit illegible chars as required)
                        if open_spans.get(FromEdition) or open_spans.get(EditorCompleted):
                            new_char.dipl_utf = ""
                            new_char.anno_utf = ""
                            new_char.illegible = True
                        elif open_spans.get(Strikethrough):
                            new_char.anno_utf = ""
                            new_char.anno_simple = ""
                            new_char.strikethrough = True

                    if new_char is None:
                        raise RuntimeError("Unexpected parse error. This should never happen! {0}, {1}".format(key, intoken))
                    else:
                        myparse.append(new_char)
                    break  # <- exactly one char should result from each match

            if new_char is None:
                logging.warning("Empty char results from " + intoken)

        if any(val for key, val in open_spans.items()):
            raise ParseError("Unclosed bracket at end of token: " + intoken)

        if output_type.startswith("dipl"):
            result = DiplTrans(myparse, subtoken=subtoken_spans)
        elif output_type.startswith("anno"):
            result = AnnoTrans(myparse)
        else:
            myparse = self.tokenize(myparse)
            result = Trans(myparse, subtoken=subtoken_spans)
        try:
            self.validate(result, output_type)  # throws ParseError
        except ParseError as e:
            raise ParseError("The token '{0}' could not be parsed:\n\t{1}".format(intoken,
                             e.message))
        return result

    def tokenize(self, some_parse):

        padded_parse = [Whitespace("")] + some_parse + [Whitespace("")]

        for i in range(1, len(padded_parse) - 1):
            last_char, this_char, next_char = padded_parse[i-1:i+2]

            if isinstance(last_char, (UniverbSpace, UniverbNewline, Hyphen,
                                    # if hyphens are dipl bounds, these should be too
                                    #   (also present in handschrift)
                                      MultiverbNewline)):
                this_char.dipl_bound = True

            # word split "foo|bar"
            if isinstance(last_char, (MultiverbSpace, MultiverbNewline)):
                this_char.anno_bound = True

            # other initial punctuation
            if (isinstance(last_char, Whitespace) and
                not isinstance(last_char, LineBreak) and
                isinstance(this_char, Punct) and
                not isinstance(next_char, Punct)):
                next_char.anno_bound = True

            # final punctuation  "foo%." (NOT "f%.oo")
            if ((isinstance(last_char, TextChar) or 
                (isinstance(last_char, Bracket) and not last_char.opening)) and
                isinstance(this_char, Punct) and
                not isinstance(next_char, TextChar)):
                this_char.anno_bound = True

            # separate punct from punct (if different)
            if (isinstance(last_char, Punct) and
                isinstance(this_char, Punct) and
                last_char.string != this_char.string):
                this_char.anno_bound = True

            # separate punct after ptk
            if (isinstance(last_char, ParticleLink) and
                isinstance(this_char, Punct)):
                this_char.anno_bound = True

            # preeditionszeichen
            #  (with special handling of initial quotation marks)
            if (isinstance(last_char, (Whitespace, MultiverbSpace)) and
                isinstance(this_char, QuotationMark)):
                next_char.anno_bound = True
            elif (isinstance(this_char, SentBound)):
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
        self.missing_br_open = {'['}

        # self.spc_re = r"(?P<spc> \s+ )"
        # self.abbr_re = r'(?P<abbr> \. [\w$] \. | <<\.{3}>> | \[\[\.\.\.\]\] )'
        # self.comm_re = r'(?P<comm> [+@][KEZ] )'
        # self.word_re = r'(?P<w> . \\\ [^\[\](){}<>] | . )'
        # self.init_punc_re = r'(?P<ip> // | \*C | \*f )'
        # self.punc_re = (r'(?P<p>  \. \\\ . | %\. | \. | (?<! \\\ ) / | ' + BULLET + ' | .̇ | ' +
        #         MEDIUS + ' | ' + ELEVATUS +  ' | ' + PARAGRAPHUS +
        #         r' | ! | \? | : | ;  )')
        # self.strk_re = r'(?P<strk>  \*\[ | \*\] )'
        # # NB: messy lookahead fix for symbols ending with open parens
        # self.preedit_re = (r'(?P<pe> \([.;!?:,"«»]\) | ,,\) | ,,\( (?![.;!?:,"«»]) | ' +
        #             r',\) | ,\( (?![.;!?:,"«»]) | ,, | , )')
        # self.ptk_marker_re = r'(?P<ptk> \*1 | \*2 )'
        # self.brackets_re = r'(?P<br> \[+ | \]+ | <+ | >+ )'
        # self.quotes_re = r'(?P<q> " | « | » )'
        # self.majuscule_re = r'(?P<m> [*÷] [{(<] (?: [a-zA-Z] \\\ . | [a-zA-Z] )+ [*÷] \d* [})>] )'
        # self.editnum_re = r'(?P<edit> (?<![\*÷]) \{ [^{} ]+ (?<![\*÷]) \} )'
        # self.splitter_re = r'(?P<spl> ~\(=\) | ~\|+ | ~ | \(=\) | =\|+ | \# | \|+ )'
        # self.ddash_re = r'(?P<dd> = )'

        # # specifies which regexes are to be applied, and in what order
        # self.re_parts = [self.spc_re, self.abbr_re, self.comm_re, self.majuscule_re,
        #                  self.splitter_re, self.ddash_re, self.quotes_re,
        #                  self.strk_re, self.preedit_re, self.init_punc_re, self.punc_re,
        #                  self.ptk_marker_re, self.brackets_re, self.word_re]

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
        self.allowed.update('()')

class AnselmParser(RexParser):
    pass

class RediParser(RexParser):
    pass


## Assigns parsers to dialects
dialect_mapper = {None: PlainParser,
                  "plain": PlainParser,
                  "rem": RemParser,
                  "ref": RefParser,
                  "redi": RediParser,
                  "anselm": AnselmParser}
