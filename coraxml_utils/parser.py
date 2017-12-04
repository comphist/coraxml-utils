class RemToken(BaseToken):
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


class RexToken(BaseToken, metaclass=abc.ABCMeta):

    def __init__(self, intoken):
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

    def validate(self):
        pass

