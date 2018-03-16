
import re
import logging

class RexTokenizer:

    def __init__(self):

        self.token_bound = re.compile(r"[ \t]+", re.VERBOSE)
        self.line_bound = re.compile(r"(?<! \(=\) | .=\| | ..= )[ \t]*\n[ \t]*", re.VERBOSE)
        self.comment_re = re.compile(r"([+@])([KEZ])")
        self.shifttagopen_re = re.compile(r"\+([FLRÜMQ]p?)")
        self.shifttagclose_re = re.compile(r"@([FLRÜMQ]p?)")

    def tokenize(self, inputtext):
        result = list()
        open_comment = None
        token_or_line = re.compile("({}|{})".format(self.token_bound.pattern, 
                                                    self.line_bound.pattern),
                                   re.VERBOSE)
        last_chunk = ""
        for chunk in token_or_line.split(inputtext):
            comm_match = self.comment_re.match(chunk)
            stopen_match = self.shifttagopen_re.match(chunk)
            stclose_match = self.shifttagclose_re.match(chunk)

            if comm_match:
                if comm_match.group(1) == "+":
                    if open_comment:
                        logging.error("Comment of type '{0}' opens inside '{1}'-type comment".format(
                                        comm_match.group(2), open_comment.type))
                    else:
                        # open new comment
                        open_comment = Comment(comm_match.group(2))

                else:
                    if open_comment:
                        # close comment
                        if open_comment.type != comm_match.group(2):
                            logging.error("Comment of type '{0}' closes with '{1}' tag".format(
                                                open_comment.type, comm_match.group(2)))
                        result.append(open_comment)
                        open_comment = None
                    else:
                        logging.error("Comment '%s' closed but wasn't opened", comm_match.group(2))

            elif open_comment:
                result.append(chunk)

            elif stopen_match:
                result.append(ShiftTagOpen(stopen_match.group(1)))
            elif stclose_match:
                result.append(ShiftTagClose(stclose_match.group(1)))

            elif self.token_bound.match(chunk):
                if "\t" in chunk:
                    logging.warning("Tab used to separate tokens after " + last_chunk)
                result.append(Whitespace(chunk))
            elif self.line_bound.match(chunk):
                if chunk != "\n":
                    logging.warning("Extra whitespace at line break after " + last_chunk)
                result.append(Whitespace("\n", newline=True))

            else:                
                if chunk:
                    result.append(Token(chunk))
                else:
                    logging.warning("Empty token near " +  last_chunk)

            last_chunk = chunk
        return result


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