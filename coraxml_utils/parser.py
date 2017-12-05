
import re
import abc

from coraxml_utils.character import replacements
from coraxml_utils.parsed_token import ParsedToken

MEDIUS = "\u00b7"
ELEVATUS = "\uf161"
PARAGRAPHUS = "\uf1e1"
BULLET = "\u2219"  # used strangely often in REM
ALPHA = "abcdefghijklmnopqrstuvwxyz"

BR = {'[': ']', ']': '[', 
      '(': ')', ')': '(',
      '{': '}', '}': '{',
      '<': '>', '>': '<'}

class ParseError(Exception):
    def __init__(self, msg):
        self.message = msg


class BaseParser:

    def __init__(self):
        self.token_re = re.compile(r"( (?x) " + "|".join(self.re_parts) + ")")

    def flip_bracket(self, br_str):
        return "".join(BR.get(c, c) for c in br_str)

    def parse(self, intoken):
        if isinstance(intoken, str):
            myparse = list()
            open_brackets = list()
            open_br_types = list()
            next_char_br = None
            in_comment = False

            for match in re.finditer(self.token_re, intoken):
                for key, val in match.groupdict().items():
                    if val:
                        new_char = None

                        # disallow brackets that span multiple tokens
                        if key == "spc":
                            if open_brackets:
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

                        # handling span-based annotations
                        elif key == "strk":
                            if val == "*[":
                                open_brackets.append(val)
                                open_br_types.append("strk")
                                next_char_br = val
                            else:
                                open_brackets.pop()
                                open_br_types.pop()
                                myparse[-1]["after"] = val

                        elif key == "br":
                            if re.search(r"[\[<]", val):
                                open_brackets.append(val)
                                open_br_types.append("ill")
                                next_char_br = val
                            else:
                                open_br = open_brackets.pop()
                                if open_br != self.flip_bracket(val):
                                    print("non-matching brackets!", intoken)
                                open_br_types.pop()
                                myparse[-1]["after"] = val
                                if open_brackets or open_br_types:
                                    print("verschachtelte klammern:", intoken)

                        elif key.startswith('uni'):
                            new_char_index = int(key[3:])
                            # special case for punc w/ utf conversions
                            if "." in val or "·" in val:
                                mytype = "p"
                            else:
                                mytype = "w"
                            new_char = {"trans": val, "type": mytype, 
                                        "simple": replacements[new_char_index][2],
                                        "utf": replacements[new_char_index][1]}

                        elif key == "maj":
                            maj_letter = re.sub(r"[*÷][{(<]([A-Za-zÄÖÜäöüß$]{,3})[*÷]\d*[})>]", 
                                                r"\1", val)
                            new_char = {"trans": val, "type": key,
                                        "simple": maj_letter,
                                        "utf": maj_letter}
                        else:
                            new_char = {"trans": val, "type": key, 
                                        "simple": val, "utf": val}

                        if new_char:
                            if open_brackets:
                                new_char["br"] = open_brackets[-1]
                                new_char["brtype"] = open_br_types[-1]

                            if next_char_br:
                                new_char["before"] = next_char_br
                                next_char_br = None

                            myparse.append(new_char)

            if open_brackets:
                raise ParseError("Unclosed bracket at end of token: " + intoken)

            result = ParsedToken(myparse, illegible_replacement=self.ILLEGIBLE_REPLACEMENT)
            self.validate(result)  # throws ParseError
            return result


    def validate(self, obj):
        # remove all valid characters, now everything that remains
        # is an error. also remove \&1-9 "variables zeichen"
        # which gets simplified to {1-9}
        # and %[A-Z] which is code for a superscript capital
        # note that superscript capitals are unchanged because unicode does
        # not support superscripting of arbitrary characters
        test_string = obj.to_string(character="simple", 
                                     preedpunc=False, 
                                     preedtoken=False,
                                     editnum=False)
        if isinstance(self, RediParser):
            test_string = re.sub(r"{[1-9][0-9]?}", "", test_string)
        else:
            test_string = re.sub(r"{[1-9]}", "", test_string)
        test_string = re.sub(r"%[A-Z]", "", test_string)
        test_string = re.sub(self.ESCAPE_CHAR, "", test_string)
        invalid_chars = set(test_string) - self.allowed

        if invalid_chars:
            raise ParseError("Transcription contains invalid characters: " + 
                             str(sorted(invalid_chars)))


class RemParser(BaseParser):
    def __init__(self, intoken):
        self.ATOMIC_ILLEGIBLE = "<<...>>"
        self.ILLEGIBLE_REPLACEMENT = "[...]"
        self.missing_br_open = {'['}

        self.spc_re = r"(?P<spc> \s+ )"
        self.abbr_re = r'(?P<abbr> \. [\w$] \. | <<\.{3}>> | \[\[\.\.\.\]\] )'
        self.comm_re = r'(?P<comm> [+@][KEZ] )'
        self.word_re = r'(?P<w> . \\\ [^\[\](){}<>] | . )'
        self.init_punc_re = r'(?P<ip> // | \*C | \*f )'
        self.punc_re = (r'(?P<p>  \. \\\ . | %\. | \. | (?<! \\\ ) / | ' + BULLET + ' | .̇ | ' +
                MEDIUS + ' | ' + ELEVATUS +  ' | ' + PARAGRAPHUS +
                r' | ! | \? | : | ;  )')
        self.strk_re = r'(?P<strk>  \*\[ | \*\] )'
        # NB: messy lookahead fix for symbols ending with open parens
        self.preedit_re = (r'(?P<pe> \([.;!?:,"«»]\) | ,,\) | ,,\( (?![.;!?:,"«»]) | ' +
                    r',\) | ,\( (?![.;!?:,"«»]) | ,, | , )')
        self.ptk_marker_re = r'(?P<ptk> \*1 | \*2 )'
        self.brackets_re = r'(?P<br> \[+ | \]+ | <+ | >+ )'
        self.quotes_re = r'(?P<q> " | « | » )'
        self.majuscule_re = r'(?P<m> [*÷] [{(<] (?: [a-zA-Z] \\\ . | [a-zA-Z] )+ [*÷] \d* [})>] )'
        self.editnum_re = r'(?P<edit> (?<![\*÷]) \{ [^{} ]+ (?<![\*÷]) \} )'
        self.splitter_re = r'(?P<spl> ~\(=\) | ~\|+ | ~ | \(=\) | =\|+ | \# | \|+ )'
        self.ddash_re = r'(?P<dd> = )'

        # specifies which regexes are to be applied, and in what order
        self.re_parts = [self.spc_re, self.abbr_re, self.comm_re, self.majuscule_re,
                         self.splitter_re, self.ddash_re, self.quotes_re,
                         self.strk_re, self.preedit_re, self.init_punc_re, self.punc_re,
                         self.ptk_marker_re, self.brackets_re, self.word_re]

        self.ESCAPE_CHAR = re.compile(r"&([^" + re.escape("".join(self.allowed)) + r"])")

        super().__init__(intoken)

        # in REM, [[...]] is often used (apparently erroneously) to
        # denote missing letters or lines, so here I replace such 
        # instances with the correct abbr, [...]
        new_parse = list()
        for c in self.parse:
            if c["type"] == "abbr" and c["char"] == "[[...]]":
                c["char"] = "[...]"
            new_parse.append(c)
        self.parse = new_parse


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
        word_re = r'(?P<w> \\ . | . )'
        uni_re = "|".join("(?P<uni{0}>".format(i) + x + ")"
                            for i, (x, _, _) in enumerate(replacements)) 

        init_punc_re = r'(?P<ip> // | \*[Cf] )' 
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
        quotes_re = r'(?P<q> \( ' + quotes + r' \) | ' + quotes + ')'
        majuscule_re = r'(?P<maj> [*÷] [{(<]' + alpha + r'{,3} [*÷] \d* [})>] )'
        # majuscule_re = r'(?P<maj> [*÷] [{(<] | (?<= [*÷] [{(<] ' + alpha + r'+) [*÷] \d* [})>] )'
        editnum_re = r'(?P<edit> (?<![\*÷]) \{ [^{}]+ (?<![\*÷]) \} )'
        splitter_re = r'(?P<spl> ~\(=\) | ~\|+ | ~ | (?<!\|) \(=\) (?!\|) | =\|+ | \# | \|+ (?!=) )'
        ddash_re = r'(?P<dd> = )'

        # specifies which regexes are to be applied, and in what order
        self.re_parts = [spc_re, abbr_re, comm_re, majuscule_re,
                         editnum_re, splitter_re, ddash_re, quotes_re,
                         strk_re, preedit_re, init_punc_re, 
                         ptk_marker_re, brackets_re, uni_re, punc_re, word_re]

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

        super().__init__()

    def validate(self):
        pass
