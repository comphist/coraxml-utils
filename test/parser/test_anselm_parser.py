import unittest

from coraxml_utils.parser import *


class ParserTest(unittest.TestCase):

    def test_pro_error(self):
        """Make sure that not all p's are simplified to pro"""

        test_string = "zer$panten"
        tok = AnselmParser().parse(test_string)
        self.assertEquals(tok.tokenize_anno()[0].simple(), "zerspanten")

        test_string = "enpei$$en"
        tok = AnselmParser().parse(test_string)
        self.assertEquals(tok.tokenize_anno()[0].simple(), "enpeissen")
