
import re
import abc

from coraxml_utils.character import convert

MEDIUS = "\u00b7"
ELEVATUS = "\uf161"
PARAGRAPHUS = "\uf1e1"
BULLET = "\u2219"  # used strangely often in REM
ALPHA = "abcdefghijklmnopqrstuvwxyz"

BR = {'[': ']', ']': '[', 
      '(': ')', ')': '(',
      '{': '}', '}': '{',
      '<': '>', '>': '<'}

# DIPL_TRANS_OPTS = Options(character="orig", syllab=False, tokenize="historical",
#                           illegible="original", strikethru="original",
#                           doubledash="leave", preedtoken="leave")

# DIPL_UTF_OPTS = Options(character="utf", syllab=False, tokenize="historical", 
#                         illegible="character", strikethru="leave", 
#                         doubledash="leave", preedpunc="delete", preedtoken="delete")

# MOD_TRANS_OPTS = Options(character="orig", tokenize="all", 
#                          illegible="original", strikethru="delete", 
#                          doubledash="leave", preedtoken="leave", preedpunc="leave",
#                          nosplitinit=True)

# MOD_SIMPLE_OPTS = Options(character="simple", tokenize="all",  
#                           illegible="leave", strikethru="delete", 
#                           doubledash="delete", preedtoken="delete", preedpunc="leave",
#                           nosplitinit=True)

# MOD_UTF_OPTS = Options(character="utf", tokenize="all", 
#                        illegible="character", strikethru="delete", 
#                        doubledash="delete", preedtoken="delete", preedpunc="leave",
#                        nosplitinit=True)

__version__ = "2017.11.21"


class ParseError(Exception):
    def __init__(self, msg):
        self.message = msg


class BaseToken:
    def __init__(self, intoken):
        self.token_re = re.compile(r"( (?x) " + "|".join(self.re_parts) + ")")
        self.errors = list()

        if isinstance(intoken, str):
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
        return self.to_string(illegible="original", 
                              character="original",
                              doubledash=True,
                              editnum=True,
                              strikethru="original",
                              preedpunc=True,
                              preedtoken=True)


    def set_illegible_options(self, opt_ill, opt_char):
        # setting illegible options:
        #   lists contain bracket types for which each
        #   action (one list per action) is to be carried out

        br_actions = {"leave": list(),
                      "delete": list(),
                      "original": list()}

        if opt_ill == "delete":
            br_actions["delete"] = ["<", "<<", "[", "[["]
        elif opt_ill == "leave":
            br_actions["leave"] = ["<", "<<", "[", "[["]
        elif opt_ill == "original":
            br_actions["original"] = ["<", "<<", "[", "[["]
        elif opt_ill == "character":
            if opt_char == "utf":
                br_actions["delete"] = ["[", "[["]
                br_actions["leave"] = ["<", "<<"]
            elif opt_char == "simple":
                br_actions["leave"] = ["<", "["]
                br_actions["original"] = ["[[", "<<"]
            else:
                # the character/orig combo should lead here
                br_actions["original"] = ["<", "<<",  "[", "[["]
        else:
            br_actions["leave"] = ["<", "<<", "[", "[["]  
        return br_actions        


    def to_string(self, 
                  illegible="leave", 
                  character="utf",
                  doubledash=False,
                  editnum=False,
                  strikethru="leave",
                  preedpunc=True,
                  preedtoken=False):
        br_actions = self.set_illegible_options(illegible, character)

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
                if character != "original":
                    out_char = re.sub(r"[*÷][{(<]([A-Za-zÄÖÜäöüß$]{,3})[*÷]\d*[})>]", 
                                       r"\1", c["char"])

            if not doubledash and c["type"] == "dd":
                skip_char = True

            if not editnum and c["type"] == "edit":
                skip_char = True

            brtype = c.get("brtype", None)
            # strikethru
            if brtype == "strk":
                if strikethru == "original":
                    before = c.get("before", "")
                    after = c.get("after", "")
                elif strikethru == "delete":
                    skip_char = True

            # illegible character handling        
            elif brtype == "ill":
                if c["br"] in br_actions["original"]:
                    before = c.get("before", "")
                    after = c.get("after", "")
                # if last char is bracket end
                elif c.get("br") in br_actions["delete"] and i == last_index:
                    before = self.ILLEGIBLE_REPLACEMENT
                    skip_char = True
                elif c.get("br") in br_actions["delete"]:
                    # wait for bracket end, then add replacement (see below)
                    skip_char = True
                else:
                    if last_char.get("br") in br_actions["delete"]:
                        before = self.ILLEGIBLE_REPLACEMENT
            else:
                if last_char.get("br") in br_actions["delete"]:
                    before = self.ILLEGIBLE_REPLACEMENT

            # pre-edition char handling
            if not preedpunc:
                if c["type"] in {"pe", "q"}:
                    skip_char = True

            if not preedtoken:
                if (c["char"] == "*f" or
                    c["type"] == "ptk" or
                    c["type"] == "spl"):
                    skip_char = True

            outstr.append(before)
            if not skip_char:
                outstr.append(out_char)
            outstr.append(after)

            last_char = c

        # token-wise conversion to target
        if character != "original":
            return convert("".join(outstr), character).strip()
        else:
            return "".join(outstr).strip()


    def validate(self):
        # remove all valid characters, now everything that remains
        # is an error. also remove \&1-9 "variables zeichen"
        # which gets simplified to {1-9}
        # and %[A-Z] which is code for a superscript capital
        # note that superscript capitals are unchanged because unicode does
        # not support superscripting of arbitrary characters
        test_string = self.to_string(character="simple", 
                                     preedpunc=False, 
                                     preedtoken=False,
                                     editnum=False)
        if isinstance(self, RediToken):
            test_string = re.sub(r"{[1-9][0-9]?}", "", test_string)
        else:
            test_string = re.sub(r"{[1-9]}", "", test_string)
        test_string = re.sub(r"%[A-Z]", "", test_string)
        test_string = re.sub(self.ESCAPE_CHAR, "", test_string)
        invalid_chars = set(test_string) - self.allowed

        if invalid_chars:
            raise ParseError("Transcription contains invalid characters: " + 
                             str(sorted(invalid_chars)))


    def keep(self, *types):
        return self.__class__([c for c in self.parse if c["type"] in types])


    def has(self, *types):
        return any(c["type"] in types for c in self.parse)
        

    def delete(self, *types):
        return self.__class__([c for c in self.parse if c["type"] not in types])


    def flip_bracket(self, br_str):
        return "".join(BR.get(c, c) for c in br_str)


    def tokenize(self, tokenize_type="all", split_init_punc=True):
        new_parse = list()
        padded_parse = ([{"char": "", "type": "spc"}] + 
                        self.parse + 
                        [{"char": "", "type": "spc"}])

        for i in range(1, len(padded_parse) - 1):
            last_char, this_char, next_char = padded_parse[i-1:i+2]

            my_bracket = this_char.get("br", None)
            conditions = []
            postspace_conds = []

            if (tokenize_type == "medium" or 
                tokenize_type == "all"):
                # word split "foo|bar"
                conditions.append(last_char["type"] == "spl" and 
                                  last_char["char"].endswith("|"))

                if tokenize_type == "all":
                    if split_init_punc:
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

            elif tokenize_type == "historical":
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

        new_tokens = list()
        stack = list()
        for c in new_parse:
            if c["type"] == "spc":
                if stack:
                    new_tokens.append(self.__class__(stack))
                    stack = list()
            else:
                stack.append(c)
        new_tokens.append(self.__class__(stack))
        return new_tokens


class RemToken(BaseToken):
    def __init__(self, intoken):
        self.ATOMIC_ILLEGIBLE = "<<...>>"
        self.ILLEGIBLE_REPLACEMENT = "[...]"
        self.missing_br_open = {'['}

        self.spc_re = r"(?P<spc> \s+ )"
        self.abbr_re = r'(?P<abbr> \. [\w$] \. | <<\.{3}>> | \[\[\.\.\.\]\] )'
        self.comm_re = '(?P<comm> [+@][KEZ] )'
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


class RexToken(BaseToken, metaclass=abc.ABCMeta):

    def __init__(self, intoken):
        self.ILLEGIBLE_REPLACEMENT = "[...]"
        self.missing_br_open = {'['}

        alpha = r"[A-Za-zÄÖÜäöüß$]"
        punc = r'[.;!?:,]'
        quotes = r'["«»]'
        no_pq = r'(?![.;!?:,"«»])'

        spc_re = r"(?P<spc> \s+ )"
        abbr_re = '(?P<abbr>' + '|'.join(['%\.' + alpha + '\%.', 
                                          '\.' + alpha + '\.',
                                          '\[\.{3}\]',
                                          '%[A-Z]']) + ')'
        comm_re = r'(?P<comm> [+@][KEZ] )'
        word_re = r'(?P<w> \\ . | . )'
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
        editnum_re = r'(?P<edit> (?<![\*÷]) \{ [^{}]+ (?<![\*÷]) \} )'
        splitter_re = r'(?P<spl> ~\(=\) | ~\|+ | ~ | (?<!\|) \(=\) (?!\|) | =\|+ | \# | \|+ (?!=) )'
        ddash_re = r'(?P<dd> = )'

        # specifies which regexes are to be applied, and in what order
        self.re_parts = [spc_re, abbr_re, comm_re, majuscule_re,
                         editnum_re, splitter_re, ddash_re, quotes_re,
                         strk_re, preedit_re, init_punc_re, punc_re,
                         ptk_marker_re, brackets_re, word_re]

        # LIST OF ALLOWED CHARACTERS FOR validity check
        self.allowed = set(ALPHA)
        self.allowed.update(ALPHA.upper())
        self.allowed.update('-",.:;\/!?1234567890ßäöüÄÖÜ ')
        # for r-kuerzung
        self.allowed.update("'")

        self.ESCAPE_CHAR = re.compile(r"&([^" + re.escape("".join(self.allowed)) + r"])")

        self.init_parser()

        super().__init__(intoken)

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


class PlainToken(BaseToken):
    def __init__(self, intoken):
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

        super().__init__(intoken)
