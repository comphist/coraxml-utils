
import re

class RexTokenizer:

    def __init__(self):

        self.token_bound = re.compile(r"[ ]+", re.VERBOSE)
        self.line_bound = re.compile(r"(?<! \(=\) | .=\| | ..= )\n", re.VERBOSE)
        self.comment_re = re.compile(r"[+@]([KEZ])")
        self.shifttagopen_re = re.compile(r"\+([FLRÜMQ]p?)")
        self.shifttagclose_re = re.compile(r"@([FLRÜMQ]p?)")

    def tokenize(self, inputtext):
        result = list()
        open_comment = None
        token_or_line = re.compile("({}|{})".format(self.token_bound.pattern, 
                                                    self.line_bound.pattern),
                                   re.VERBOSE)
        for chunk in token_or_line.split(inputtext):
            comm_match = self.comment_re.match(chunk)
            stopen_match = self.shifttagopen_re.match(chunk)
            stclose_match = self.shifttagclose_re.match(chunk)

            if comm_match:
                if open_comment:
                    result.append(open_comment)
                    open_comment = None
                else:
                    open_comment = Comment(comm_match.group(1))

            elif stopen_match:
                result.append(ShiftTagOpen(stopen_match.group(1)))

            elif stclose_match:
                result.append(ShiftTagClose(stclose_match.group(1)))

            elif open_comment:
                    open_comment.content.append(chunk)
            elif self.token_bound.match(chunk):
                result.append(Whitespace(chunk))
            elif self.line_bound.match(chunk):
                result.append(Whitespace(chunk, newline=True))
            else:   
                result.append(Token(chunk))
            
        return result


class Token:
    def __init__(self, _mystring):
        self.string = _mystring

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return self.string

    def __eq__(self, obj):

        if not isinstance(Token, object):
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

        if not isinstance(Whitespace, object):
            return False
        else:
            return (self.string == obj.string) and (self.is_newline == obj.is_newline)


class Comment: 
    def __init__(self, _mytype):
        self.type = _mytype
        self.content = list()

    def __str__(self):
        return "<{0} content={1}>".format(self.type, " ".join(self.content))

    def __repr__(self):
        return str(self)


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