
import re
import abc
import logging
logging.basicConfig(format='%(levelname)s: %(message)s')
logger = logging.getLogger()

from collections import defaultdict

from coraxml_utils.character import replacements
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
        test_string = "".join(c["anno_simple"] 
                              for c in obj.parse
                              if c.get("type") not in {"pe", "ptk", "edit", "spl",
                                                       "[", "[[", "<", "<<", "abbr"})
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
            raise ParseError("Transcription contains invalid characters: " + 
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
        comm_re = r'(?P<comm> [+@][KEZ] )'
        word_re = r'(?P<w> \*f | \\ . | . )'
        uni_re = "|".join("(?P<uni{0}>".format(i) + x + ")"
                            for i, (x, _, _) in enumerate(replacements) if x) 
        inu_re = "|".join("(?P<inu{0}>".format(i) + x + ")"
                            for i, (_, x, _) in enumerate(replacements) if x)

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
        # brackets_re = r'(?P<br> \[+ (?![ ]) | (?<![ ]) \]+ | <+ (?![ ]) | (?<![ ]) >+ )'
        brackets_re = r'(?P<br> \[+ | \]+ | <+ | >+ )'
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
                         ptk_marker_re, brackets_re, uni_re, punc_re, inu_re,
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
                        open_spans[val].append(match.start())
                        new_char = {"trans": val, 
                                    "dipl_utf": "",
                                    "anno_utf": "",
                                    "anno_simple": "",
                                    "type": "*["}

                    elif val == "*]":
                        closing = open_spans["*["].pop()
                        subtoken_spans.append(SubtokenAnno("*[", closing, match.end()))
                        new_char = {"trans": val, 
                                    "dipl_utf": "",
                                    "anno_utf": "",
                                    "anno_simple": "",
                                    "type": "*["}

                    elif val in {"<", "<<"}:
                        open_spans[val].append(match.start())
                        new_char = {"trans": val, 
                                    "dipl_utf": "",
                                    "anno_utf": "",
                                    "anno_simple": "",
                                    "type": val}
                    elif val in {">", ">>"}:
                        openbr = flip_bracket(val)
                        closing = open_spans[openbr].pop()
                        subtoken_spans.append(SubtokenAnno(openbr, closing, match.end()))
                        new_char = {"trans": val, 
                                    "dipl_utf": "",
                                    "anno_utf": "",
                                    "anno_simple": "",
                                    "type": openbr}
                    elif val in {"[", "[["}:
                        open_spans[val].append(match.start())
                        new_char = {"trans": val, 
                                    "dipl_utf": self.ILLEGIBLE_REPLACEMENT,
                                    "anno_utf": self.ILLEGIBLE_REPLACEMENT,
                                    "anno_simple": "",
                                    "type": val}
                    elif val in {"]", "]]"}:
                        openbr = flip_bracket(val)
                        closing = open_spans[openbr].pop()
                        subtoken_spans.append(SubtokenAnno(openbr, closing, match.end()))                        
                        new_char = {"trans": val,
                                    "dipl_utf": "",
                                    "anno_utf": "",
                                    "anno_simple": "",
                                    "type": openbr}

                    elif key == "dd":
                        new_char = {"trans": val,
                                    "dipl_utf": val,
                                    "anno_utf": "",
                                    "anno_simple": "",
                                    "type": "dd"}
                    elif key in {"pe", "q"}:
                        new_char = {"trans": val,
                                    "dipl_utf": "",
                                    "anno_utf": val,
                                    "anno_simple": val,
                                    "type": key}
                    elif key in {"ptk", "spl"} or val == "*f":
                        new_char = {"trans": val,
                                    "dipl_utf": "",
                                    "anno_utf": "",
                                    "anno_simple": "",
                                    "type": key}

                    else:
                        if key.startswith("uni"):
                            _, utfchar, simplechar = replacements[int(key[3:])]
                            new_char = {"trans": val,
                                        "dipl_utf": utfchar,
                                        "anno_utf": utfchar,
                                        "anno_simple": simplechar,
                                        # special case for punc w/ utf conversions
                                        "type": "p" if "." in val or "·" in val else "w"} 
                        elif key.startswith("inu"):
                            _, _, simplechar = replacements[int(key[3:])]
                            new_char = {"trans": val, # for the lack of a better alternative
                                        "dipl_utf": val,
                                        "anno_utf": val,
                                        "anno_simple": simplechar,
                                        "type": "w"}
                        elif key == "maj":
                            maj_letter = re.sub(r"[*÷][{(<]([A-Za-zÄÖÜäöüß$]{,3})[*÷]\d*[})>]", 
                                                r"\1", val)
                            new_char = {"trans": val,
                                        "dipl_utf": maj_letter.replace("$", "\u017F"),
                                        "anno_utf": maj_letter.replace("$", "\u017F"),
                                        "anno_simple": maj_letter.replace("$", "s"),
                                        "type": key}
                        else:
                            new_char = {"trans": val,
                                        "dipl_utf": val,
                                        "anno_utf": val,
                                        "anno_simple": val,
                                        "type": key}

                        # process open spans (omit illegible chars as required)
                        if open_spans["["] or open_spans["[["]:
                            new_char["dipl_utf"] = ""
                            new_char["anno_utf"] = ""
                        elif open_spans["*["]:
                            new_char["anno_utf"] = ""
                            new_char["anno_simple"] = ""

                    myparse.append(new_char)

        if any(val for key, val in open_spans.items()):
            raise ParseError("Unclosed bracket at end of token: " + intoken)

        if output_type.startswith("dipl"):
            result = DiplTrans(myparse, subtoken=subtoken_spans)
        elif output_type.startswith("anno"):
            result = AnnoTrans(myparse)
        else:
            dipl_spl, anno_spl = self.tokenize(myparse)
            result = Trans(myparse, 
                           anno_splits=anno_spl, dipl_splits=dipl_spl,
                           subtoken=subtoken_spans)
        self.validate(result)  # throws ParseError
        return result
        

    def tokenize(self, some_parse, split_init_punc=True):

        padded_parse = ([{"trans": "", "type": "spc"}] + 
                        some_parse + 
                        [{"trans": "", "type": "spc"}])
        dipl_tok_bounds = list()
        anno_tok_bounds = list()

        for i in range(1, len(padded_parse) - 1):
            last_char, this_char, next_char = padded_parse[i-1:i+2]

            my_bracket = this_char.get("br")

            if last_char["type"] == "spl" and last_char["trans"].endswith('#'):
                dipl_tok_bounds.append(i)

            if this_char["type"] == "dd":
                dipl_tok_bounds.append(i)

            # word split "foo|bar"
            if last_char["type"] == "spl" and last_char["trans"].endswith("|"):
                anno_tok_bounds.append(i)

            if split_init_punc:
                # initial punctuation "//foo"
                if last_char["type"] in {"ip", "q"}:
                    anno_tok_bounds.append(i)

            # other initial punctuation
            if (last_char["type"] in {"spc", None} and
                this_char["type"] == "p" and this_char["trans"] != "." and 
                next_char["type"] == "w"):
                anno_tok_bounds.append(i)

            # final punctuation  "foo%." (NOT "f%.oo")
            if (last_char["type"] not in {"br", "spc", "spl"} and
                this_char["type"] in {"ip", "p", "pe", "q"} and this_char["trans"] != '.' and
                next_char["type"] != "w" and next_char["trans"] not in {'(=)', '#'}):
                anno_tok_bounds.append(i)

            # rule for periods (which can be periods or unreadable chars)
            if (last_char["type"] not in {"spc", "spl"} and
                  this_char["trans"] == "." and 
                  next_char["type"] != "w" and 
                  this_char["trans"] != last_char["trans"] and # group same chars
                  next_char["trans"] not in {'(=)', '#'} and
                   # tokenize when period not in missing char parens
                  (my_bracket not in self.missing_br_open or
                   # tokenize when period is alone in parens
                   (this_char.get("before") and 
                    this_char.get("after") and
                    this_char.get("brtype") == "ill"))):
                anno_tok_bounds.append(i)

            # ptk marker after punctuation  "foo.*2"
            if this_char["type"] == "ptk" and last_char["type"] in {"ip", "p", "pe", "q"}:
                anno_tok_bounds.append(i)

            # always tokenize on whitespace 
            if this_char["type"] == "spc":
                anno_tok_bounds.append(i)
                dipl_tok_bounds.append(i)

        return dipl_tok_bounds, anno_tok_bounds



class RediParser(RexParser):
    def init_parser(self):
        self.missing_br_open = {'[[', '<<'}


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

        dipl_tok_bounds = list()
        anno_tok_bounds = list()

        for i in range(0, len(some_parse) - 1):

            # tokenize on whitespace
            if some_parse[i]["type"] == "spc":
                ## why + 2?
                anno_tok_bounds.append(i + 2)
                dipl_tok_bounds.append(i + 2)

        return dipl_tok_bounds, anno_tok_bounds

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
                    new_char = {"trans": val,
                                "dipl_utf": val,
                                "anno_utf": val,
                                "anno_simple": val,
                                "type": key}

                    myparse.append(new_char)

        if output_type.startswith("dipl"):
            result = DiplTrans(myparse, subtoken=subtoken_spans)
        elif output_type.startswith("anno"):
            result = AnnoTrans(myparse)
        else:
            dipl_spl, anno_spl = self.tokenize(myparse)
            result = Trans(myparse, 
                           anno_splits=anno_spl, dipl_splits=dipl_spl,
                           subtoken=subtoken_spans)
        self.validate(result)  # throws ParseError
        return result