
import re

class RexTokenizer:

	def __init__(self):

		self.token_bound = re.compile(r"(?<!\(=\) | .=\| | ..= )[ \n]", re.VERBOSE)
		self.comment_re = re.compile(r"[+@][KEZ]")
		self.shifttagopen_re = re.compile(r"\+([FLRÜMQ]p?)")
		self.shifttagclose_re = re.compile(r"@([FLRÜMQ]p?)")

	def tokenize(self, inputtext):
		result = list()
		open_comment = None
		for chunk in self.token_bound.split(inputtext):

			if self.comment_re.match(chunk):
				if open_comment:
					open_comment.content.append(chunk)
					result.append(open_comment)
					open_comment = None
				else:
					open_comment = Comment(mytype)

			elif self.shifttagopen_re.match(chunk):
				result.append(ShiftTagOpen(chunk))

			elif self.shifttagclose_re.match(chunk):
				result.append(ShiftTagClose(chunk))

			else:
				if open_comment:
					open_comment.content.append(chunk)
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