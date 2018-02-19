
import re
import abc
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


def flip_bracket(br_str):
    return "".join({'[': ']', ']': '[', 
                    '(': ')', ')': '(',
                    '{': '}', '}': '{',
                    '<': '>', '>': '<'}.get(c, c) for c in br_str)


class ParseError(Exception):
    def __init__(self, msg):
        self.message = msg


class BaseParser:

    def __init__(self):
        self.token_re = re.compile(r"( (?x) " + "|".join(self.re_parts) + ")")

    def validate(self, obj):
        # remove all valid characters, now everything that remains
        # is an error. also remove \&1-9 "variables zeichen"
        # which gets simplified to {1-9}
        # and %[A-Z] which is code for a superscript capital
        # note that superscript capitals are unchanged because unicode does
        # not support superscripting of arbitrary characters
        test_string = "".join(c.anno_simple
                              for c in obj.parse
                              if not isinstance(c, MetaChar))
        if isinstance(self, RediParser):
            test_string = re.sub(r"{[1-9][0-9]?}", "", test_string)
        else:
            test_string = re.sub(r"{[1-9]}", "", test_string)
        test_string = re.sub(r"%[A-Z]", "", test_string)
        test_string = re.sub(self.ESCAPE_CHAR, "", test_string)

        # allow foreign language marking
        test_string = re.sub(r"\*f", "", test_string)
        invalid_chars = set(test_string) - self.allowed

        if invalid_chars:
            raise ParseError("Transcription " + obj.trans() + " contains invalid characters: " +
                             str(sorted(invalid_chars)))




class RexParser(BaseParser, metaclass=abc.ABCMeta):

    def __init__(self):
        self.ILLEGIBLE_REPLACEMENT = "[...]"
        self.missing_br_open = {'['}

        alpha = r"[A-Za-zÄÖÜäöüß$]"
        punc = r'[.;!?:,]'
        quotes = r'["«»]'
        no_pq = r'(?![.;!?:,"«»])'

        spc_re = r"(?P<spc> \s+ )"
        abbr_re = '(?P<abbr>' + '|'.join(['%\.' + alpha + '%\.', 
                                          '\.' + alpha + '\.',
                                          '\[\.{3}\]',
                                          '%[A-Z]']) + ')'
        # comm_re = r'(?P<comm> [+@][KEZ] )'
        word_re = r'(?P<w> \*f | \\ . | . )'
        uni_re = "|".join("(?P<uni{0}>".format(i) + x + ")"
                            for i, (x, _, _) in enumerate(replacements) if x) 
        # inu_re = "|".join("(?P<inu{0}>".format(i) + x + ")"
        #                     for i, (_, x, _) in enumerate(replacements) if x)

        # init_punc_re = r'(?P<ip> // | \*[Cf] )' 
        punc_re = r'(?P<p> %\. | / | ' + punc +')'
        strk_re = r'(?P<strk>  \*[\[ | \*\]] )'
        preedit_re = r'(?P<pe>' + '|'.join(['\(' + punc + '\)',
                                            ',,\)', 
                                            ',,\(' + no_pq,
                                            ',\)',
                                            ',\(' + no_pq,
                                            ',,']) + ')'
        ptk_marker_re = r'(?P<ptk> \*1 | \*2 )'
        brackets_re = r'(?P<br> \[+ (?![ ]) | (?<![ ]) \]+ | <+ (?![ ]) | (?<![ ]) >+ )'
        # brackets_re = r'(?P<br> \[+ | \]+ | <+ | >+ )'
        quotes_re = r'(?P<q> \( ' + quotes + r' \) | ' + quotes + ')'
        majuscule_re = r'(?P<maj> [*÷] [{(<]' + alpha + r'{,3} [*÷] \d* [})>] )'
        # majuscule_re = r'(?P<maj> [*÷] [{(<] | (?<= [*÷] [{(<] ' + alpha + r'+) [*÷] \d* [})>] )'
        editnum_re = r'(?P<edit> (?<![\*÷]) \{ [^{}]+ (?<![\*÷]) \} )'
        splitter_re = r'(?P<spl> ~\(=\) | ~\|+ | ~ | (?<!\|) \(=\) (?!\|) | =\|+ | \# | \|+ (?!=) )'
        ddash_re = r'(?P<dd> = )'

        # specifies which regexes are to be applied, and in what order
        self.re_parts = [spc_re, abbr_re, comm_re, majuscule_re,
                         editnum_re, splitter_re, ddash_re, quotes_re,
                         strk_re, preedit_re,
                         ptk_marker_re, brackets_re, uni_re, punc_re,
                         word_re]

        # LIST OF ALLOWED CHARACTERS FOR validity check
        self.allowed = set(ALPHA)
        self.allowed.update(ALPHA.upper())
        self.allowed.update('-",.:;\/!?1234567890ßäöüÄÖÜ ')
        # for r-kuerzung
        self.allowed.update("'")

        self.ESCAPE_CHAR = re.compile(r"&([^" + re.escape("".join(self.allowed)) + r"])")

        self.init_parser()

        super().__init__()

    @abc.abstractmethod
    def init_parser(self):
        pass


    def parse(self, intoken, output_type="trans"):
        """
        output_type: {"trans", "dipl", "anno"}
        """
        myparse = list()
        subtoken_spans = list() # list of SubtokenAnnos
        open_spans = defaultdict(list)    # list of tuples, (type, start)
        in_comment = False
        new_char = None

        for match in re.finditer(self.token_re, intoken):
            for key, val in match.groupdict().items():
                if val:
                    # disallow brackets that span multiple tokens
                    if key == "spc":
                        if any(val for key, val in open_spans.items()):
                            raise ParseError("Unclosed bracket at end of token: " + intoken)

                    # ensures that nothing in a comment gets processed
                    if key == "comm":
                        if val.startswith("+"):
                            in_comment = True
                        else:
                            in_comment = False
                        myparse.append({"trans": val, "type": key})
                    elif in_comment:
                        myparse.append({"trans": val, "type": "w"})         
                                
                    if val == "*[":
                        new_char = Strikethrough(val, opening=True)
                        open_spans["*["].append(match.start())
                    elif val == "*]":
                        if "*[" in open_spans:
                            closing = open_spans["*["].pop()
                        else:
                            raise ParseError("Closed *] is not opened: " + intoken)
                        subtoken_spans.append(SubtokenAnno("*[", closing, match.end()))
                        new_char = Strikethrough(val, opening=True)
                    elif val in {"<", "<<"}:
                        open_spans[val].append(match.start())
                        new_char = Illegible(val, opening=True)
                    elif val in {">", ">>"}:
                        openbr = flip_bracket(val)
                        closing = open_spans[openbr].pop()
                        subtoken_spans.append(SubtokenAnno(openbr, closing, match.end()))
                        new_char = Illegible(val, opening=False)
                    elif val in {"[", "[["}:
                        open_spans[val].append(match.start())
                        new_char = Illegible(val, opening=True,
                                             dipl_utf=self.ILLEGIBLE_REPLACEMENT,
                                             anno_utf=self.ILLEGIBLE_REPLACEMENT)
                    elif val in {"]", "]]"}:
                        openbr = flip_bracket(val)
                        if open_spans[openbr]:
                            closing = open_spans[openbr].pop()
                        else:
                            raise ParseError("Closing bracket is not opened: " + intoken)
                        subtoken_spans.append(SubtokenAnno(openbr, closing, match.end())) 
                        new_char = Illegible(val, opening=False)

                    elif key == "dd":
                        new_char = Hyphen(val, dipl_utf=val)
                    elif key in {"pe", "q"}:
                        # TODO: what to do with qmarks? not sent bounds?
                        new_char = SentBound(val, anno_utf=val, anno_simple=val)
                    elif key == "ptk" or val == "*f":
                        new_char = MetaChar(val)

                    elif key == "spl":
                        if key == "(=)":
                            new_char = EditHyphen(val)
                        elif key == "=|":
                            new_char = DiplJoiner(val)
                        else:
                            new_char = TokenBound(val)
                    else:
                        if key.startswith("uni"):
                            _, utfchar, simplechar = replacements[int(key[3:])]
                            # special case for punc w/ utf conversions
                            if val != "\\." and "." in val or "·" in val:
                                new_char = Punct(val, dipl_utf=utfchar, anno_utf=utfchar,
                                                 anno_simple=simplechar)
                            else:
                                new_char = TextChar(val, dipl_utf=utfchar, anno_utf=utfchar, 
                                                    anno_simple=simplechar)
                        elif key == "maj":
                            maj_match = re.search(r"[*÷][{(<]([A-Za-zÄÖÜäöüß$]{,3})[*÷](\d*)[})>]", val)
                            maj_letter = maj_match.group(1)
                            mysize = maj_match.group(2)

                            new_char = Majuscule(val, size=mysize,
                                                 dipl_utf=maj_letter.replace("$", "\u017F"),
                                                 anno_utf=maj_letter.replace("$", "\u017F"),
                                                 anno_simple=maj_letter.replace("$", "s"))
                        else:
                            if key == "w":
                                new_char = TextChar(val, dipl_utf=val, anno_utf=val,
                                                    anno_simple=val)
                            elif key == "edit":
                                new_char = MetaChar(val, dipl_utf=val, anno_utf=val,
                                                    anno_simple=val)                        
                            elif key == "p":
                                # TODO: need some way to recognize periods that stand for missing
                                        # chars at this point!
                                new_char = Punct(val, dipl_utf=val, anno_utf=val,
                                                    anno_simple=val)
                            else:
                                ParseError("Unknown key: " + key)

                        # process open spans (omit illegible chars as required)
                        if open_spans["["] or open_spans["[["]:
                            new_char.dipl_utf = ""
                            new_char.anno_utf = ""
                            new_char.illegible = True
                        elif open_spans["*["]:
                            new_char.anno_utf = ""
                            new_char.anno_simple = ""
                            new_char.strikethrough = True

                    myparse.append(new_char)

        if any(val for key, val in open_spans.items()):
            raise ParseError("Unclosed bracket at end of token: " + intoken)

        if output_type.startswith("dipl"):
            result = DiplTrans(myparse, subtoken=subtoken_spans)
        elif output_type.startswith("anno"):
            result = AnnoTrans(myparse)
        else:
            myparse = self.tokenize(myparse)
            result = Trans(myparse, subtoken=subtoken_spans)
        self.validate(result)  # throws ParseError
        return result
        

    def tokenize(self, some_parse, split_init_punc=True):

        padded_parse = [Whitespace("")] + some_parse + [Whitespace("")]

        for i in range(1, len(padded_parse) - 1):
            last_char, this_char, next_char = padded_parse[i-1:i+2]

            if isinstance(last_char, TokenBound):
                if last_char.string.endswith('#'):
                    this_char.dipl_bound = True

                elif last_char.string == '(=)':
                    this_char.dipl_bound = True

                # word split "foo|bar"
                elif last_char.string.endswith("|"):
                    this_char.anno_bound = True

            if isinstance(last_char, Hyphen):
                this_char.dipl_bound = True

            #  TODO: reactivate/update (esp. for REM)
            # if split_init_punc:
            #     # initial punctuation "//foo"
            #     if last_char["type"] in {"ip", "q"}:
            #         anno_tok_bounds.append(i)

            # other initial punctuation
            if (isinstance(last_char, Whitespace) and
                isinstance(this_char, Punct) and 
                isinstance(next_char, TextChar)):
                next_char.anno_bound = True

            # final punctuation  "foo%." (NOT "f%.oo")
            if (isinstance(last_char, TextChar) and
                isinstance(this_char, Punct) and
                not isinstance(next_char, TextChar)):
                this_char.anno_bound = True


            # always tokenize on whitespace 
            # TODO: should result in completely new token though, right?
            # if isinstance(this_char, Whitespace):
            #     this_char.anno_bound = True
            #     this_char.dipl_bound = True

        return some_parse



class RediParser(RexParser):
    def init_parser(self):
        self.missing_br_open = {'[[', '<<'}
        self.allowed.update("()")


class AnselmParser(RexParser):
    def init_parser(self):
        self.ATOMIC_ILLEGIBLE = ""
        self.missing_br_open = {'<', '<<', '[', '[['}
        self.allowed.update("()")


class RefParser(RexParser):
    def init_parser(self):
        self.missing_br_open = {'[', '<<'}
        self.allowed.update("()")


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

        self.ESCAPE_CHAR = re.compile(r"&([^" + re.escape("".join(self.allowed)) + r"])")

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
        open_spans = defaultdict(list)    # list of tuples, (type, start)
        in_comment = False
        new_char = None

        for match in re.finditer(self.token_re, intoken):
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



## List of parser for given dialects
dialect_mapper = {None: PlainParser,
                  "plain": PlainParser,
                  "rem": RemParser,
                  "ref": RefParser,
                  "redi": RediParser,
                  "anselm": AnselmParser}

