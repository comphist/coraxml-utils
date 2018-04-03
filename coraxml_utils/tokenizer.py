
import regex
import logging


class RexTokenizer:
    def __init__(self):
        self.token_re = r"(?P<tok> [^\s{+@][^\s+@]* )"
        self.joiner_re = r"\[?\[? ( \(=\) | =\| | = ) \]?\]? [ \t]*\n[ \t]*"
        self.token_lineend_re = r"(?P<tokl> " + self.token_re + self.joiner_re + self.token_re + r")"
        self.lineend_re = r"(?P<end> [ \t]*\n[ \t]* )"
        self.wspace_re = r"(?P<sp> [ \t] )"
        self.secedit_number_re = r"(?P<secedit> \{ [^}*÷]+ \} )"
        self.shifttagopen_re = r"(?P<sto> \+(?P<sotyp>[FLRÜMQ]p?) )"
        self.shifttagclose_re = r"(?P<stc> @(?P<sctyp>[FLRÜMQ]p?) )"
        self.comment_re = r"(?P<com> \+(?P<cotyp>[KEZ]) (?P<ctxt>[^\n@]+) @(?P<cctyp>[KEZ]) )"

        re_parts = [self.comment_re, self.shifttagopen_re, self.shifttagclose_re, self.token_lineend_re,
                    self.token_re,  self.secedit_number_re, self.wspace_re, self.lineend_re]
        self.tokenize_re = regex.compile("|".join(re_parts), flags=regex.VERBOSE)

    def tokenize(self, inputtext):
        result = list()
        last_token = ""
        last_shifttags = list()
        for match in self.tokenize_re.scanner(inputtext):
            matchlabels = match.capturesdict()

            if matchlabels["com"]:
                if matchlabels["cotyp"][0] != matchlabels["cctyp"][0]:
                    logging.error("Comment opening ({0}) and closing ({1}) tag types do not match".format(
                        matchlabels["cotyp"][0], matchlabels["cctyp"][0]
                    ))

                if not isinstance(result[-1], Whitespace):
                    logging.warning("Comment after '{0}' is not preceded by whitespace".format(result[-1]))

                result.append(Comment(matchlabels["cotyp"][0], 
                                      matchlabels["ctxt"][0].strip()))
            
            elif matchlabels["sto"]:
                result.append(ShiftTagOpen(matchlabels["sotyp"][0]))
                last_shifttags.append(matchlabels["sotyp"][0])

            elif matchlabels["stc"]:
                try:
                    last_shifttag = last_shifttags.pop()
                except IndexError:
                    logging.error("Shifttag '{0}' closes but wasn't opened".format(matchlabels["sctyp"][0]))
                if last_shifttag != matchlabels["sctyp"][0]:
                    logging.error("Shifttag opening ({0}) and closing ({1}) tag types do not match".format(
                        last_shifttag, matchlabels["sctyp"][0]
                    ))
                result.append(ShiftTagClose(matchlabels["sctyp"][0]))
            
            elif matchlabels["secedit"]:
                result.append(Comment("Z", matchlabels["secedit"][0]))

            elif matchlabels["tokl"]:
                result.append(Token(matchlabels["tokl"][0]))
                last_token = matchlabels["tokl"][0]

            elif matchlabels["tok"]:
                result.append(Token(matchlabels["tok"][0]))
                last_token = matchlabels["tok"][0]

            elif matchlabels["sp"]:
                chunk = matchlabels["sp"][0]
                if "\t" in chunk:
                    logging.warning("Tab used to separate tokens after '{0}'".format(last_token))
                result.append(Whitespace(chunk))

            elif matchlabels["end"]:
                chunk = matchlabels["end"][0]
                if chunk != "\n":
                    logging.warning("Extra whitespace at line break after '{0}'".format(last_token))
                    # corrects anomalous line breaks
                    chunk = "\n"
                result.append(Whitespace(chunk, newline=True))

            else:
                logging.warning("Unknown entity in " + matchlabels)

        if last_shifttags:
            logging.error("Shifttags {0} still open at end of document".format(last_shifttags))
                        
        return result


class RediTokenizer(RexTokenizer):

    def __init__(self):
        super().__init__()
        # self.secedit_number_re = re.compile(r"^\{ (?!\d\d?\}) (\{ [^{}]* [^ {}\*÷] \})", re.VERBOSE)

        # accounts for special abbrevs. in Redi texts, e.g. {2}
        self.token_re = r"(?P<tok> [^\s{][^\s]* | \{\d\d?\} )"
        # secedit ordered later so token regex can find abbrevs
        re_parts = [self.comment_re, self.shifttagopen_re, self.shifttagclose_re, self.token_lineend_re,
            self.token_re,  self.secedit_number_re, self.wspace_re, self.lineend_re]
        self.tokenize_re = regex.compile("|".join(re_parts), flags=regex.VERBOSE)


class Token:
    def __init__(self, _mystring):
        self.string = _mystring

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return self.string

    def __eq__(self, obj):
        if obj is None:
            return False
        elif not isinstance(obj, Token):
            return False
        else:
            return self.string == obj.string


class Whitespace:
    def __init__(self, _mystring, newline=False):
        self.string = _mystring
        self.is_newline = newline

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return self.string

    def __eq__(self, obj):
        if obj is None:
            return False
        elif not isinstance(obj, Whitespace):
            return False
        else:
            return (self.string == obj.string) and (self.is_newline == obj.is_newline)


class Comment: 
    def __init__(self, _mytype, content=None):
        self.type = _mytype
        if content:
            self.content = content
        else:
            self.content = str()

    def __str__(self):
        return "<{0} content={1}>".format(self.type, self.content)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if other:
            if isinstance(other, self.__class__):
                return (self.type == other.type and 
                        self.content == other.content)
            else:
                return False
        else:
            return False


class ShiftTag:
    def __init__(self, _mytype):
        self.type = _mytype

    def __str__(self):
        return self.type

    def __repr__(self):
        return self.type

class ShiftTagOpen(ShiftTag):
    pass

class ShiftTagClose(ShiftTag):
    pass