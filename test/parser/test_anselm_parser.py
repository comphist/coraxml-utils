import unittest

from coraxml_utils.parser import *


class ParserTest(unittest.TestCase):

    def _create_anselm_parse(test_string):

        tok = AnselmParser().parse(test_string)
        return tok

    def test_pro_error(self):
        """Make sure that not all p's are simplified to pro"""

        tok = ParserTest._create_anselm_parse("zer$panten")
        self.assertEquals(tok.tokenize_anno()[0].simple(), "zerspanten")

        tok = ParserTest._create_anselm_parse("enpei$$en")
        self.assertEquals(tok.tokenize_anno()[0].simple(), "enpeissen")

    def test_strikethrough_tokenization(self):
        """Make sure that no mod-tokens are created if whole token is marked as strike through."""

        tok = ParserTest._create_anselm_parse("*[$we$ter*]")
        self.assertEquals(len(tok.tokenize_anno()), 0)

    def test_line_split_preedition(self):

        tok = ParserTest._create_anselm_parse("hymel(=)reich")
        self.assertEquals(len(tok.tokenize_dipl()), 2)
