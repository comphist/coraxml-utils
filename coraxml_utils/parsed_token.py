
import re
import abc

import character
from settings import Options

MEDIUS = "\u00b7"
ELEVATUS = "\uf161"
PARAGRAPHUS = "\uf1e1"
BULLET = "\u2219"  # used strangely often in REM
ALPHA = "abcdefghijklmnopqrstuvwxyz"

BR = {'[': ']', ']': '[', 
      '(': ')', ')': '(',
      '{': '}', '}': '{',
      '<': '>', '>': '<'}

DIPL_TRANS_OPTS = Options(character="orig", syllab=False, tokenize="historical",
                          illegible="original", strikethru="original",
                          doubledash="leave", preedtoken="leave")

DIPL_UTF_OPTS = Options(character="utf", syllab=False, tokenize="historical", 
                        illegible="character", strikethru="leave", 
                        doubledash="leave", preedpunc="delete", preedtoken="delete")

MOD_TRANS_OPTS = Options(character="orig", tokenize="all", 
                         illegible="original", strikethru="delete", 
                         doubledash="leave", preedtoken="leave", preedpunc="leave",
                         nosplitinit=True)

MOD_SIMPLE_OPTS = Options(character="simple", tokenize="all",  
                          illegible="leave", strikethru="delete", 
                          doubledash="delete", preedtoken="delete", preedpunc="leave",
                          nosplitinit=True)

MOD_UTF_OPTS = Options(character="utf", tokenize="all", 
                       illegible="character", strikethru="delete", 
                       doubledash="delete", preedtoken="delete", preedpunc="leave",
                       nosplitinit=True)

__version__ = "2017.11.21"


class ParseError(Exception):
    def __init__(self, msg):
        self.message = msg


class BaseToken:
    def __init__(self, intoken, options):
        self.token_re = re.compile(r"( (?x) " + 
                              r" | ".join([r"(?P<spc> \s+ )",
                                           self.abbr_re,
                                           self.comm_re,
                                           self.majuscule_re,
                                           self.editnum_re,
                                           self.splitter_re,
                                           self.ddash_re,
                                           self.quotes_re,
                                           self.strk_re,
                                           self.preedit_re,
                                           self.init_punc_re,
                                           self.punc_re,
                                           self.ptk_marker_re,
                                           self.brackets_re,
                                           self.word_re]) + r" )")

        self.options = options
        self.allowed.update(self.options.allowed)
        self.errors = list()
        if isinstance(intoken, str):

            self.original_str = intoken
            
            self.parse = list()
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
                                raise ParseError("Unclosed bracket at end of token")

                        # ensures that nothing in a comment gets processed
                        if key == "comm":
                            if val.startswith("+"):
                                in_comment = True
                            else:
                                in_comment = False
                            self.parse.append({"char": val, "type": key})
                        elif in_comment:
                            self.parse.append({"char": val, "type": "w"})

                        # handling span-based annotations
                        elif key == "strk":
                            if val == "*[":
                                open_brackets.append(val)
                                open_br_types.append("strk")
                                next_char_br = val
                            else:
                                open_brackets.pop()
                                open_br_types.pop()
                                self.parse[-1]["after"] = val

                        elif key == "br":
                            if re.search(r"[\[<]", val):
                                open_brackets.append(val)
                                open_br_types.append("ill")
                                next_char_br = val
                            else:
                                open_brackets.pop()
                                open_br_types.pop()
                                self.parse[-1]["after"] = val
                        else:
                            new_char = {"char": val, "type": key}

                        if new_char:
                            if open_brackets:
                                new_char["br"] = open_brackets[-1]
                                new_char["brtype"] = open_br_types[-1]

                            if next_char_br:
                                new_char["before"] = next_char_br
                                next_char_br = None

                            self.parse.append(new_char)

            if open_brackets:
                raise ParseError("Unclosed bracket at end of token")

            self.validate()

        elif isinstance(intoken, list):
            self.parse = intoken
            self.options = Options(**options.__dict__)
            self.errors = list()
        else:
            self.parse = None


    def __len__(self):
        return len(self.parse)


    def __eq__(self, other):
        return self.parse == other.parse


    def __repr__(self):
        return str(self.parse)


    def __str__(self):
        self.set_illegible_options()

        # this is done here to make sure that it happens *after*
        # any tokenization has taken place
        self.handle_character_options()

        last_char = dict()
        outstr = list()
        last_index = len(self.parse) - 1

        for i, c in enumerate(self.parse):
            before = ""
            after = ""
            out_char = c["char"]
            skip_char = False

            # majuscule handling
            if c["type"] == "maj":
                if self.options.character != "orig":
                    out_char = re.sub(r"[*÷][{(<]([A-Za-zÄÖÜäöüß$]{,3})[*÷]\d*[})>]", 
                                       r"\1", c["char"])

            if self.options.doubledash == "delete" and c["type"] == "dd":
                skip_char = True

            if ((self.options.editnum == "delete" or 
                 self.options.bibinfo == "none") and c["type"] == "edit"):
                skip_char = True

            brtype = c.get("brtype", None)
            # strikethru
            if brtype == "strk":
                if self.options.strikethru == "original":
                    before = c.get("before", "")
                    after = c.get("after", "")
                elif self.options.strikethru == "delete":
                    skip_char = True

            # illegible character handling        
            elif brtype == "ill":
                if c["br"] in self.br_orig:
                    before = c.get("before", "")
                    after = c.get("after", "")
                # if last char is bracket end
                elif c.get("br") in self.br_delete and i == last_index:
                    before = self.ILLEGIBLE_REPLACEMENT
                    skip_char = True
                elif c.get("br") in self.br_delete:
                    # wait for bracket end, then add replacement (see below)
                    skip_char = True
                else:
                    if last_char.get("br") in self.br_delete:
                        before = self.ILLEGIBLE_REPLACEMENT
            else:
                if last_char.get("br") in self.br_delete:
                    before = self.ILLEGIBLE_REPLACEMENT

            outstr.append(before)
            if not skip_char:
                outstr.append(out_char)
            outstr.append(after)

            last_char = c

        # token-wise conversion to target
        if self.options.character != "orig":
            return character.convert("".join(outstr), self.options.character).strip()
        else:
            return "".join(outstr).strip()


    def validate(self):
        # remove all valid characters, now everything that remains
        # is an error. also remove \&1-9 "variables zeichen"
        # which gets simplified to {1-9}
        # and %[A-Z] which is code for a superscript capital
        # note that superscript capitals are unchanged because unicode does
        # not support superscripting of arbitrary characters
        test_string = str(self.with_opts(Options(character="simple", 
                                                 preedpunc="delete", 
                                                 preedtoken="delete",
                                                 editnum="delete")))
        if isinstance(self, RediToken):
            test_string = re.sub(r"{[1-9][0-9]?}", "", test_string)
        else:
            test_string = re.sub(r"{[1-9]}", "", test_string)
        test_string = re.sub(r"%[A-Z]", "", test_string)
        test_string = re.sub(self.options.ESCAPE_CHAR, "", test_string)
        invalid_chars = set(test_string) - self.options.allowed

        if invalid_chars:
            raise ParseError("Transcription contains invalid characters: " + 
                             str(sorted(invalid_chars)))


    def set_illegible_options(self):
        # lists contain bracket types for which each
        # action (one list per action) is to be carried out
        self.br_leave = list()
        self.br_delete = list()
        self.br_orig = list()

        opt = self.options.illegible
        if opt == "delete":
            self.br_delete = ["<", "<<", "[", "[["]
        elif opt == "leave":
            self.br_leave = ["<", "<<", "[", "[["]
        elif opt == "original":
            self.br_orig = ["<", "<<", "[", "[["]
        elif opt == "character":
            if self.options.character == "utf":
                self.br_delete = ["[", "[["]
                self.br_leave = ["<", "<<"]
            elif self.options.character == "simple":
                self.br_leave = ["<", "["]
                self.br_orig = ["[[", "<<"]
            else:
                # the character/orig combo should lead here
                self.br_orig = ["<", "<<",  "[", "[["]
        else:
            self.br_leave = ["<", "<<", "[", "[["]


    def handle_character_options(self):
        if self.options.preedpunc == "delete":
            self.parse = [c for c in self.parse 
                          if c["type"] not in {"pe", "q"}]

        if self.options.preedtoken == "delete":
            self.parse = [c for c in self.parse
                          if (c["char"] != "*f" and 
                              c["type"] != "ptk" and 
                              c["type"] != "spl")]


    def with_opts(self, options):
        return self.__class__(self.parse, options)


    def keep(self, *types):
        return self.__class__([c for c in self.parse if c["type"] in types], 
                              self.options)


    def has(self, *types):
        return any(c["type"] in types for c in self.parse)
        

    def delete(self, *types):
        return self.__class__([c for c in self.parse if c["type"] not in types], 
                              self.options)


    def flip_bracket(self, br_str):
        return "".join(BR.get(c, c) for c in br_str)


    def tokenize(self):
        new_parse = list()
        padded_parse = [{"char": "", "type": "spc"}] + self.parse + [{"char": "", "type": "spc"}]

        for i in range(1, len(padded_parse) - 1):
            last_char, this_char, next_char = padded_parse[i-1:i+2]

            my_bracket = this_char.get("br", None)
            conditions = []
            postspace_conds = []

            if (self.options.tokenize == "medium" or 
                self.options.tokenize == "all"):
                # word split "foo|bar"
                conditions.append(last_char["type"] == "spl" and 
                                  last_char["char"].endswith("|"))

                if self.options.tokenize == "all":
                    if not self.options.nosplitinit:
                        # initial punctuation "//foo"
                        conditions.append(last_char["type"] in {"ip", "q"})

                    # other initial punctuation
                    postspace_conds.append(last_char["type"] in {"spc", None} and
                                           this_char["type"] == "p" and
                                           this_char["char"] != "." and 
                                           next_char["type"] == "w")

                    # final punctuation  "foo%." (NOT "f%.oo")
                    conditions.append(last_char["type"] not in {"br", "spc", "spl"} and
                                      this_char["type"] in {"ip", "p", "pe", "q"} and 
                                      this_char["char"] != '.' and
                                      next_char["type"] != "w" and
                                      next_char["char"] not in {'(=)', '#'})

                    # rule for periods (which can be periods or unreadable chars)
                    conditions.append(last_char["type"] not in {"spc", "spl"} and
                                      this_char["char"] == "." and 
                                      next_char["type"] != "w" and 
                                      next_char["char"] not in {'(=)', '#'} and
                                       # tokenize when period not in missing char parens
                                      (my_bracket not in self.missing_br_open or
                                       # tokenize when period is alone in parens
                                       (this_char.get("before") and 
                                        this_char.get("after") and
                                        this_char.get("brtype") == "ill")))

                    # ptk marker after punctuation  "foo.*2"
                    conditions.append(this_char["type"] == "ptk" and 
                                      last_char["type"] in {"ip", "p", "pe", "q"})

            elif self.options.tokenize == "historical":
                conditions.append(last_char["type"] == "spl" and 
                                  last_char["char"].endswith('#'))

            else:
                # do nothing -- no tokenization
                pass

            this_char_copy = this_char.copy()  # prevents tokenization side-effects
            if any(conditions):
                if my_bracket:
                    if new_parse:
                        # close bracket before space
                        new_parse[-1]["after"] = self.flip_bracket(my_bracket)

                    # reopen after space
                    this_char_copy["before"] = my_bracket

                new_parse.append({"char": " ", "type": "spc"})
                new_parse.append(this_char_copy)

            elif any(postspace_conds):
                new_parse.append(this_char_copy)
                new_parse.append({"char": " ", "type": "spc"})
            else:
                new_parse.append(this_char_copy)

        return self.__class__(new_parse, self.options)


class RemToken(BaseToken):
    def __init__(self, intoken, options):
        self.ATOMIC_ILLEGIBLE = "<<...>>"
        self.ILLEGIBLE_REPLACEMENT = "[...]"
        self.missing_br_open = {'['}

        self.abbr_re = '(?P<abbr> \. [\w$] \. | <<\.{3}>> | \[\[\.\.\.\]\] )'
        self.comm_re = '(?P<comm> [+@][KEZ] )'
        self.word_re = '(?P<w> . \\\ [^\[\](){}<>] | . )'
        self.init_punc_re = '(?P<ip> // | \*C | \*f )'
        self.punc_re = ('(?P<p>  \. \\\ . | %\. | \. | (?<! \\\ ) / | ' + BULLET + ' | .̇ | ' +
                MEDIUS + ' | ' + ELEVATUS +  ' | ' + PARAGRAPHUS +
                ' | ! | \? | : | ;  )')
        self.strk_re = '(?P<strk>  \*\[ | \*\] )'
        # NB: messy lookahead fix for symbols ending with open parens
        self.preedit_re = ('(?P<pe> \([.;!?:,"«»]\) | ,,\) | ,,\( (?![.;!?:,"«»]) | ' +
                    ',\) | ,\( (?![.;!?:,"«»]) | ,, | , )')
        self.ptk_marker_re = '(?P<ptk> \*1 | \*2 )'
        self.brackets_re = '(?P<br> \[+ | \]+ | <+ | >+ )'
        self.quotes_re = '(?P<q> " | « | » )'
        self.majuscule_re = '(?P<m> [*÷] [{(<] (?: [a-zA-Z] \\\ . | [a-zA-Z] )+ [*÷] \d* [})>] )'
        self.editnum_re = '(?P<edit> (?<![\*÷]) \{ [^{} ]+ (?<![\*÷]) \} )'
        self.splitter_re = '(?P<spl> ~\(=\) | ~\|+ | ~ | \(=\) | =\|+ | \# | \|+ )'
        self.ddash_re = '(?P<dd> = )'

        super().__init__(intoken, options)

        # in REM, [[...]] is often used (apparently erroneously) to
        # denote missing letters or lines, so here I replace such 
        # instances with the correct abbr, [...]
        new_parse = list()
        for c in self.parse:
            if c["type"] == "abbr" and c["char"] == "[[...]]":
                c["char"] = "[...]"
            new_parse.append(c)
        self.parse = new_parse


class RexToken(BaseToken, metaclass=abc.ABCMeta):

    def __init__(self, intoken, options):
        self.ILLEGIBLE_REPLACEMENT = "[...]"
        self.missing_br_open = {'['}

        self.alpha = r"[A-Za-zÄÖÜäöüß$]"
        self.punc = r'[.;!?:,]'
        quotes = r'["«»]'
        no_pq = r'(?![.;!?:,"«»])'

        self.abbr_re = '(?P<abbr>' + '|'.join(['%\.' + self.alpha + '\%.', 
                                               '\.' + self.alpha + '\.',
                                               '\[\.{3}\]',
                                               '%[A-Z]',
                                               ]) + ')'
        self.comm_re = r'(?P<comm> [+@][KEZ] )'
        self.word_re = r'(?P<w> \\ . | . )'
        self.init_punc_re = r'(?P<ip> // | \*[Cf] )' 
        self.punc_re = r'(?P<p> %\. | / | ' + self.punc +')'
        self.strk_re = r'(?P<strk>  \*[\[ | \*\]] )'
        self.preedit_re = r'(?P<pe>' + '|'.join(['\(' + self.punc + '\)',
                                                ',,\)', 
                                                ',,\(' + no_pq,
                                                ',\)',
                                                ',\(' + no_pq,
                                                ',,']) + ')'
        self.ptk_marker_re = r'(?P<ptk> \*1 | \*2 )'
        self.brackets_re = r'(?P<br> \[+ (?![ ]) | (?<![ ]) \]+ | <+ (?![ ]) | (?<![ ]) >+ )'
        self.quotes_re = r'(?P<q> \( ' + quotes + r' \) | ' + quotes + ')'
        self.majuscule_re = r'(?P<maj> [*÷] [{(<]' + self.alpha + r'{,3} [*÷] \d* [})>] )'
        self.editnum_re = r'(?P<edit> (?<![\*÷]) \{ [^{}]+ (?<![\*÷]) \} )'
        self.splitter_re = r'(?P<spl> ~\(=\) | ~\|+ | ~ | (?<!\|) \(=\) (?!\|) | =\|+ | \# | \|+ (?!=) )'
        self.ddash_re = r'(?P<dd> = )'

        # LIST OF ALLOWED CHARACTERS FOR validity check
        self.allowed.update(ALPHA)
        self.allowed.update(ALPHA.upper())
        self.allowed.update('-",.:;\/!?1234567890ßäöüÄÖÜ ')
        # for r-kuerzung
        self.allowed.update("'")

        self.init_parser()

        super().__init__(intoken, options)

    @abc.abstractmethod
    def init_parser(self):
        pass


class RediToken(RexToken):
    def init_parser(self):
        self.missing_br_open = {'[[', '<<'}


class AnselmToken(RexToken):
    def init_parser(self):
        self.ATOMIC_ILLEGIBLE = ""
        self.missing_br_open = {'<', '<<', '[', '[['}
        self.allowed.update("()")


class RefToken(RexToken):
    def init_parser(self):
        self.missing_br_open = {'[', '<<'}
        self.allowed.update("()")

