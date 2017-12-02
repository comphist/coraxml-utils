import unittest

from coraxml_utils.parsed_token import *


class RefTokenTest(unittest.TestCase):

    def test_basic_parsing(self):
        """Make sure that parser reproduces input string"""

        test_string = "t[ok]en.(?)"
        tok = RefToken(test_string)
        self.assertEquals(str(tok), test_string)

    def test_tokenize_anno(self):

        tok = RefToken("foo|bar")
        self.assertEquals(" ".join(str(x) for x in tok.tokenize_anno()), 
                          "foo| bar")

