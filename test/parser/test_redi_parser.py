import unittest

from coraxml_utils.parser import RediParser


class RediParserTest(unittest.TestCase):

	def	test_accept_tok_wquote(self):
		myparser = RediParser()
		tok = myparser.parse('(")mensch')
		# tok2 = myparser.parse('nit(")(,)')
		
		# if tok ends up w/non-empty parse, it must be ok
		self.assertTrue(tok.parse)