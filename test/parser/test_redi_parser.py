import unittest

from coraxml_utils.parser import RediParser


class RediParserTest(unittest.TestCase):
    def _create_redi_parse(test_string):
        return RediParser().parse(test_string)

    def test_accept_tok_wquote(self):
        tok = RediParserTest._create_redi_parse('(")mensch')
        # tok2 = myparser.parse('nit(")(,)')

        # if tok ends up w/non-empty parse, it must be ok
        self.assertTrue(tok.parse)

    def test_unknown_missing_chars(self):
        tok = RediParserTest._create_redi_parse("[[...]]")
        # determine desired output
        # number tokens -> 1
        # utf -> ... ?
        self.assertEqual(len(tok.tokenize_anno()), 1)

    def test_specific_number_missing_chars(self):
        tok = RediParserTest._create_redi_parse("[[........]]")
        # number tokens -> 1
        # utf -> [...] ? or ........ ?
        self.assertEqual(len(tok.tokenize_anno()), 1)

    def test_from_edition(self):
        # each should be one token, just letters
        # -> STARB wird vnde
        tokens = [
            RediParserTest._create_redi_parse(x)
            for x in ["[[STARB]]", "wir[[d]]", "vn[[d]]e"]
        ]
        return self.assertTrue(all(len(tok.tokenize_anno()) == 1 for tok in tokens))

    def test_from_edition_mixed(self):
        tok = RediParserTest._create_redi_parse("KOBE[[R]][[..]]")
        # number tokens -> 1
        self.assertEqual(len(tok.tokenize_anno()), 1)

