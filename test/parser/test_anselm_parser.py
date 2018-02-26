import unittest

from coraxml_utils.parser import *
from coraxml_utils.coralib import Trans

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
        """
        Test handling of (=), should:
        - only occur at line end (TODO)
        - result in 2 dipls, 1 mod
        - be tagged as UL
        - not co-occur with M* symbols (TODO)
        - not occur multiple times in succession (TODO)
        """

        tok = ParserTest._create_anselm_parse("hymel(=)reich")
        self.assertEquals(len(tok.tokenize_dipl()), 2)

        # co-occurence with `|` should result in an error
        with self.assertRaises(ParseError):
            ParserTest._create_anselm_parse("hymel(=)|reich")

        with self.assertRaises(ParseError):
            ParserTest._create_anselm_parse("hymel|(=)reich")

    def test_multiverbation(self):
        tok = ParserTest._create_anselm_parse("dy\:|es")
        self.assertEquals(len(tok.tokenize_dipl()), 1)

    def test_dot_above_split(self):
        """Dot above (\.) should not be a separate anno token"""

        tok = ParserTest._create_anselm_parse("fraw\.")
        self.assertEquals(len(tok.tokenize_anno()), 1)

    def test_illegible_token(self):

        tok = ParserTest._create_anselm_parse("<...>")
        self.assertEquals(len(tok.tokenize_anno()), 1)
        self.assertEquals(len(tok.tokenize_dipl()), 1)

    def test_tokenization(self):

        tok = ParserTest._create_anselm_parse("t<o>k#en(=)iz=a|tion%....")
        self.assertEquals([x.simple() for x in tok.tokenize_anno()],
                          ["tokeniza", "tion", ".", "..."])

        self.assertEquals([str(x) for x in tok.tokenize_dipl() if x],
                          ["t<o>k#", "en(=)", "iz=", "a|tion%...."])

    def test_hochstellung(self):
        tok = ParserTest._create_anselm_parse("de%$")
        self.assertIsInstance(tok, Trans)

    def test_brackets_lineend(self):
        tok = ParserTest._create_anselm_parse("*[wi(=)\nder*]")
        