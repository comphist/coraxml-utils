import unittest

from coraxml_utils.parser import *


class ParserTest(unittest.TestCase):

    def test_basic_parsing(self):
        """Make sure that parser preserves input transcription"""

        test_string = "t[ok]en.(?)"
        tok = PlainParser().parse(test_string)
        self.assertEquals(str(tok), test_string)

    def test_basic_parsing_anselm(self):
        """Make sure that parser preserves input transcription"""
        test_string = "t[ok]en.(?)"
        tok = AnselmParser().parse(test_string)
        self.assertEquals(str(tok), test_string)    

    def test_anselm_lineend(self):
        test_string = "ma=\nria"
        tok = AnselmParser().parse(test_string)
        self.assertEqual(len(tok.tokenize_dipl()), 2)

    def test_tokenize_anno(self):
        """ TODO: ist dieser test mit dem neuen tokenizer veraltet? """
        tok = RefParser().parse("foo bar")
        self.assertEquals("|".join(str(x) for x in tok.tokenize_anno()), 
                          "foo| bar")

