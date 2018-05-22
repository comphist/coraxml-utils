import unittest

from coraxml_utils.parser import *
from coraxml_utils.coralib import Trans

class ParserTest(unittest.TestCase):

    def _create_ref_parse(test_string):
        tok = RefParser().parse(test_string)
        return tok

    def test_virgil(self):
        ## / should be separated in anno

        tok = ParserTest._create_ref_parse("Ritt'=liche\-/")
        self.assertEqual(len(tok.tokenize_anno()), 2)
        self.assertEqual(len(tok.tokenize_dipl()), 2)

    def test_virgil_in_brackets(self):
        ## / should be separated

        tok = ParserTest._create_ref_parse("*[vordír/*](.)")
        self.assertEqual(len(tok.tokenize_anno()), 3)
        self.assertEqual(len(tok.tokenize_dipl()), 1)
