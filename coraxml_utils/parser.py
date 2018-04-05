
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


# def flip_bracket(br_str):
#     return "".join({'[': ']', ']': '[', 
#                     '(': ')', ')': '(',
#                     '{': '}', '}': '{',
#                     '<': '>', '>': '<'}.get(c, c) for c in br_str)


class ParseError(Exception):
    def __init__(self, msg):
        self.message = msg


class BaseParser:

    def __init__(self):
        self.token_re = regex.compile(r"({0})".format("|".join(self.re_parts)), 
                                      flags=regex.VERBOSE)

    def validate(self, obj):
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
            if isinstance(last_char, Joiner) and not isinstance(c, LineBreak):
                # allows = mid-line as required by legacy tests
                if not isinstance(last_char, Hyphen):
                    raise ParseError("%s not at line end" % last_char.string)
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




# class RexParser(BaseParser, metaclass=abc.ABCMeta):

#     def __init__(self):
#         self.ILLEGIBLE_REPLACEMENT = "[...]"
#         self.missing_br_open = {'['}

#         alpha = r"[A-Za-zÄÖÜäöüß$]"
#         punc = r'[.;!?:,]'
#         quotes = r'["«»]'
#         no_pq = r'(?![.;!?:,"«»])'

#         spc_re = r"(?P<spc> \s+ )"
#         abbr_re = r'(?P<abbr> \.[a-zA-Z]\. | \[\.{3}\] | %[A-Z] )'
#         word_re = r'(?P<w> \*f | \\ . | . )'
#         uni_re = "|".join("(?P<uni{0}>".format(i) + x + ")"
#                             for i, (x, _, _) in enumerate(replacements) if x) 

#         punc_re = r'(?P<p> %\. | / | ' + punc +')'
#         strk_re = r'(?P<strk>  \*[\[ | \*\]] )'
#         preedit_re = r'(?P<pe> \(' + punc + r'\) | ,,\) | ,,\(' + no_pq + r'| ,\) | ,\(' + no_pq + r' | ,, )'
#         ptk_marker_re = r'(?P<ptk> \*1 | \*2 )'
#         brackets_re = r'(?P<br> \[{1,2} | \]{1,2} | <{1,2} | >{1,2} | \( | \) )'        
#         quotes_re = r'(?P<q> \( ' + quotes + r' \) | ' + quotes + ')'
#         majuscule_re = r'(?P<maj> [*÷] [{(<] (?P<majc>' + alpha + r'{,3}) [*÷] (?P<majs>\d*) [})>] )'
#         splitter_re = r'(?P<spl> ~\(=\) | ~\|+ | ~ | \(=\) | =\|+ | \# | \|+ (?!=) )'
#         ddash_re = r'(?P<dd> = )'

#         # specifies which regexes are to be applied, and in what order
#         self.re_parts = [spc_re, abbr_re, majuscule_re,
#                          splitter_re, ddash_re, quotes_re,
#                          strk_re, preedit_re, 
#                          ptk_marker_re, brackets_re, uni_re, punc_re,
#                          word_re]

#         # LIST OF ALLOWED CHARACTERS FOR validity check
#         self.allowed = set(ALPHA)
#         self.allowed.update(ALPHA.upper())
#         self.allowed.update('-",.:;\/!?1234567890ßäöüÄÖÜ\n')
#         # for r-kuerzung
#         self.allowed.update("'")

#         self.ESCAPE_CHAR = regex.compile(r"&([^" + regex.escape("".join(self.allowed)) + r"])")

#         self.init_parser()

#         super().__init__()

#     @abc.abstractmethod
#     def init_parser(self):
#         pass


#     def parse(self, intoken, output_type="trans"):
#         """
#         output_type: {"trans", "dipl", "anno"}
#         """
#         myparse = list()
#         subtoken_spans = list() # list of SubtokenAnnos
#         open_spans = defaultdict(list)    # list of tuples, (type, start)

#         for match in self.token_re.scanner(intoken):
#             new_char = None
#             skip_this_char = False
#             for key, val in match.groupdict().items():
#                 if val:
#                     # disallow brackets that span multiple tokens
#                     if key == "spc":
#                         if any(val for key, val in open_spans.items()):
#                             if "\n" in val:
#                                 raise ParseError("Unclosed bracket at end of line: " + intoken)
#                             else:
#                                 raise ParseError("Unclosed bracket at end of token: " + intoken)
#                         new_char = Whitespace(val) 
#                         if "\n" in val:
#                             new_char.line_break = True
                                
#                     elif val == "*[":
#                         new_char = Strikethrough(val, opening=True)
#                         open_spans["*["].append(match.start())
#                     elif val == "*]":
#                         if "*[" in open_spans:
#                             closing = open_spans["*["].pop()
#                         else:
#                             raise ParseError("Closed *] is not opened: " + intoken)
#                         subtoken_spans.append(SubtokenAnno("*[", closing, match.end()))
#                         new_char = Strikethrough(val, opening=False)
#                     elif val in {"<", "<<"}:
#                         open_spans[val].append(match.start())
#                         new_char = Illegible(val, opening=True)
#                     elif val in {">", ">>"}:
#                         try: 
#                             openbr = flip_bracket(val)
#                             closing = open_spans[openbr].pop()
#                             subtoken_spans.append(SubtokenAnno(openbr, closing, match.end()))
#                             new_char = Illegible(val, opening=False)
#                         except IndexError:
#                             raise ParseError("Closing bracket is not opened: " + intoken)
#                     elif val in {"[", "[["}:
#                         open_spans[val].append(match.start())
#                         new_char = Illegible(val, opening=True,
#                                              dipl_utf=self.ILLEGIBLE_REPLACEMENT,
#                                              anno_utf=self.ILLEGIBLE_REPLACEMENT)
#                     elif val in {"]", "]]"}:
#                         openbr = flip_bracket(val)
#                         if open_spans[openbr]:
#                             closing = open_spans[openbr].pop()
#                         else:
#                             raise ParseError("Closing bracket is not opened: " + intoken)
#                         subtoken_spans.append(SubtokenAnno(openbr, closing, match.end())) 
#                         new_char = Illegible(val, opening=False)

#                     elif val in {"(", ")"}:
#                         # TODO figure what should be done here
#                         if val == ")":
#                             new_char = Bracket(val, dipl_utf=val, anno_utf=val,
#                                                anno_simple=val, opening=False)
#                         else:
#                             new_char = Bracket(val, dipl_utf=val, anno_utf=val,
#                                                anno_simple=val)

#                     elif key == "dd":
#                         new_char = Hyphen(val, dipl_utf=val)
#                     elif key == "pe":
#                         new_char = SentBound(val, anno_utf=val, anno_simple=val)
#                     elif key == "q":
#                         new_char = QuotationMark(val, anno_utf=val, anno_simple=val)

#                     elif key == "ptk" or val == "*f":
#                         new_char = MetaChar(val)

#                     elif key == "spl":
#                         if val.startswith("(=)"):
#                             new_char = EditHyphen(val)
#                         elif val.startswith("=|"):
#                             new_char = DiplJoiner(val, dipl_utf="=")
#                         else:
#                             new_char = TokenBound(val)
#                     else:
#                         if key.startswith("uni"):
#                             _, utfchar, simplechar = replacements[int(key[3:])]
#                             # special case for punc w/ utf conversions
#                             if val != "\\." and "." in val or "·" in val:
#                                 new_char = Punct(val, dipl_utf=utfchar, anno_utf=utfchar,
#                                                  anno_simple=simplechar)
#                             elif "*C" in val:
#                                 new_char = Punct(val, dipl_utf=utfchar, anno_utf=utfchar,
#                                                  anno_simple=simplechar)
#                             else:
#                                 new_char = TextChar(val, dipl_utf=utfchar, anno_utf=utfchar, 
#                                                     anno_simple=simplechar)
#                         elif key == "maj":
#                             maj_letter = match.group("majc")
#                             mysize = match.group("majs")
#                             new_char = Majuscule(val, size=mysize,
#                                                  dipl_utf=maj_letter.replace("$", "\u017F"),
#                                                  anno_utf=maj_letter.replace("$", "\u017F"),
#                                                  anno_simple=maj_letter.replace("$", "s"))
#                         else:
#                             if key == "w":
#                                 new_char = TextChar(val, dipl_utf=val, anno_utf=val,
#                                                     anno_simple=val)
#                             elif key == "abbr":
#                                 new_char = TextChar(val, dipl_utf=val, anno_utf=val,
#                                                     anno_simple=val)                     
#                             elif key == "p":
#                                 # TODO: need some way to recognize periods that stand for missing
#                                         # chars at this point!
#                                 new_char = Punct(val, dipl_utf=val, anno_utf=val,
#                                                     anno_simple=val)
#                             elif key in {"majc", "majs"}:
#                                 continue
#                             else:
#                                 raise ParseError("Unknown key: '{0}' in token '{1}'".format(key, intoken))

#                         # process open spans (omit illegible chars as required)
#                         if open_spans["["] or open_spans["[["]:
#                             new_char.dipl_utf = ""
#                             new_char.anno_utf = ""
#                             new_char.illegible = True
#                         elif open_spans["*["]:
#                             new_char.anno_utf = ""
#                             new_char.anno_simple = ""
#                             new_char.strikethrough = True

#                     if new_char is None:
#                         raise RuntimeError("Unexpected parse error. This should never happen! {0}, {1}".format(key, intoken))
#                     else:
#                         myparse.append(new_char)
#                     break

#             if new_char is None:
#                 logging.warning("Empty char results from " + intoken)

#         if any(val for key, val in open_spans.items()):
#             raise ParseError("Unclosed bracket at end of token: " + intoken)

#         if output_type.startswith("dipl"):
#             result = DiplTrans(myparse, subtoken=subtoken_spans)
#         elif output_type.startswith("anno"):
#             result = AnnoTrans(myparse)
#         else:
#             myparse = self.tokenize(myparse)
#             result = Trans(myparse, subtoken=subtoken_spans)
#         try:
#             self.validate(result)  # throws ParseError
#         except ParseError as e:
#             logging.error("the token '{0}' could not be parsed:\n\t{1}".format(intoken,
#                 e.message))
#         return result
        

#     def tokenize(self, some_parse, split_init_punc=True):

#         padded_parse = [Whitespace("")] + some_parse + [Whitespace("")]

#         for i in range(1, len(padded_parse) - 1):
#             last_char, this_char, next_char = padded_parse[i-1:i+2]

#             if isinstance(last_char, TokenBound):
#                 if last_char.string.endswith('#'):
#                     this_char.dipl_bound = True

#                 elif isinstance(last_char, EditHyphen):
#                     this_char.dipl_bound = True

#                 # word split "foo|bar"
#                 elif last_char.string.endswith("|"):
#                     this_char.anno_bound = True

#             if isinstance(last_char, Hyphen):
#                 this_char.dipl_bound = True

#             # if hyphens are dipl bounds, these should be too
#             #   (also present in handschrift)
#             if isinstance(last_char, DiplJoiner):
#                 this_char.dipl_bound = True

#             # other initial punctuation
#             if (isinstance(last_char, Whitespace) and
#                 isinstance(this_char, Punct) and 
#                 not isinstance(next_char, Punct)):
#                 next_char.anno_bound = True

#             # final punctuation  "foo%." (NOT "f%.oo")
#             if (isinstance(last_char, TextChar) and
#                 isinstance(this_char, Punct) and
#                 not isinstance(next_char, TextChar)):
#                 this_char.anno_bound = True

#             # separate punct from punct
#             if (isinstance(last_char, Punct) and
#                 isinstance(this_char, Punct) and
#                 last_char.string != this_char.string):
#                 this_char.anno_bound = True

#             # separate punct after ptk
#             if (last_char.string in {"*1", "*2"} and
#                 isinstance(this_char, Punct)):
#                 this_char.anno_bound = True

#             # preeditionszeichen
#             if (isinstance(this_char, SentBound)):
#                 this_char.anno_bound = True

#         return some_parse



# class RediParser(RexParser):
#     def init_parser(self):
#         self.missing_br_open = {'[[', '<<'}
#         self.allowed.update("()")


# class AnselmParser(RexParser):
#     def init_parser(self):
#         self.ATOMIC_ILLEGIBLE = ""
#         self.missing_br_open = {'<', '<<', '[', '[['}
#         self.allowed.update("()")


# class RefParser(RexParser):
#     def init_parser(self):
#         self.missing_br_open = {'[', '<<'}
#         self.allowed.update("()")



class PlainParser(BaseParser):
    def __init__(self):
        self.ATOMIC_ILLEGIBLE = ""
        self.ILLEGIBLE_REPLACEMENT = "[...]"
        self.missing_br_open = {}

        spc_re = r"(?P<spc> \s+ )"
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

    def validate(self, obj):
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
        self.validate(result)  # throws ParseError
        return result


class RexParser(BaseParser):

    def __init__(self):
        self.ILLEGIBLE_REPLACEMENT = "[...]"
        self.missing_br_open = {'['}

        alpha = r"[A-Za-zÄÖÜäöüß$]"
        punc = r'[.;!?:,]'
        quotes = r'["«»]'
        no_pq = r'(?![.;!?:,"«»])'

        # char types
        spc_re = r"(?P<spc> [ \t]+ ) | (?P<newline> \n )"
        word_re = r'(?P<w> \.[a-zA-Z]\. | %[A-Z] | \\ . | . )'
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
        quote_re = r'(?P<q> \("\) )'
        tokenization_re = r'(?P<ul> \(=\) ) | (?P<ml> =\| ) | (?P<ms> \| ) | (?P<us> \# )'

        # sequence annotations
        strk_re = r'(?P<strko> \*\[ ) | (?P<strkc> \*\] )'
        hard_to_read_re = r'(?P<reado> < ) | (?P<readc> > )'
        edition_re = r'(?P<edito> \[ ) | (?P<editc> \] )'
        editor_completed_re = r'(?P<complo> \[\[ ) | (?P<complc> \]\] )'
        lacuna_re = r'(?P<gapo> << ) | (?P<gapc> >> )'

        # specifies which regexes are to be applied, and in what order
        self.re_parts = [spc_re, majuscule_re, tokenization_re, 
                         strk_re, hard_to_read_re, edition_re, editor_completed_re,
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
            skip_this_char = False
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
                            # openbr = flip_bracket(val)
                            closing = open_spans[Recognizable].pop()
                            subtoken_spans.append(SubtokenAnno(Recognizable, closing, match.end()))
                            new_char = Recognizable(val, opening=False)
                        except IndexError:
                            raise ParseError("Matching opening bracket missing: " + intoken)

                    elif key in {"edito", "complo", "gapo"}:
                        if key == "edito":
                            open_spans[FromEdition].append(match.start())
                            new_char = FromEdition(val, opening=True,
                                                   dipl_utf=self.ILLEGIBLE_REPLACEMENT,
                                                   anno_utf=self.ILLEGIBLE_REPLACEMENT)
                        elif key == "complo":
                            open_spans[EditorCompleted].append(match.start())
                            new_char = EditorCompleted(val, opening=True,
                                                       dipl_utf=self.ILLEGIBLE_REPLACEMENT,
                                                       anno_utf=self.ILLEGIBLE_REPLACEMENT)
                        elif key == "gapo":
                            open_spans[Lacuna].append(match.start())
                            new_char = Lacuna(val, opening=True,
                                               dipl_utf=self.ILLEGIBLE_REPLACEMENT,
                                               anno_utf=self.ILLEGIBLE_REPLACEMENT)
                    elif key in {"editc", "complc", "gapc"}:
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
                            elif key == "gapc":
                                closing = open_spans[Lacuna].pop()
                                subtoken_spans.append(SubtokenAnno(Lacuna, closing, match.end())) 
                                new_char = Lacuna(val, opening=False)
                        except IndexError:
                            raise ParseError("Closing bracket is not opened: " + intoken)


                    elif key == "pareno":
                        # TODO figure what should be done here
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
                        new_char == ParticleLink(val)
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
                            elif key == "p":
                                new_char = Punct(val, dipl_utf=val, anno_utf=val,
                                                 anno_simple=val)                    
                            elif key == "period":
                                if open_spans.get(FromEdition) or open_spans.get(EditorCompleted):
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
            self.validate(result)  # throws ParseError
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
            elif isinstance(last_char, (MultiverbSpace, MultiverbNewline)):
                this_char.anno_bound = True

            # other initial punctuation
            if (isinstance(last_char, Whitespace) and
                isinstance(this_char, Punct) and 
                not isinstance(next_char, Punct)):
                next_char.anno_bound = True

            # final punctuation  "foo%." (NOT "f%.oo")
            if (isinstance(last_char, TextChar) and
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
            if (isinstance(this_char, SentBound)):
                this_char.anno_bound = True

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
