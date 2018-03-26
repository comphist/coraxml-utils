import unittest
import logging

from coraxml_utils.tokenizer import *
from coraxml_utils.parser import ParseError


class RexTokenizerTests(unittest.TestCase):

    def setUp(self):

        self.tokenizer = tokenizer = RediTokenizer()

    def test_edition_numbering(self):
        not_comment_1 = Token("{5}")
        not_comment_2 = Token("{9}")
        comment_3 = Comment("Z", "{1vf,2}")
        comment_4 = Comment("Z", "{Kap.6,I}")
        comment_5 = Comment("Z", "{Str 7,X}")
        comment_6 = Comment("Z", "{V.10,V}")

        self.assertEquals(
            self.tokenizer.tokenize("edition numbering {5} here\nhere {9} words\nhere {1vf,2} too\nlook {Kap.6,I} here\nnext {Str 7,X} one {V.10,V}"),
            [
                Token("edition"), Whitespace(" "), Token("numbering"), Whitespace(" "), not_comment_1, Whitespace(" "), Token("here"), Whitespace("\n", True),
                Token("here"), Whitespace(" "), not_comment_2, Whitespace(" "), Token("words"), Whitespace("\n", True),
                Token("here"), Whitespace(" "), comment_3, Whitespace(" "), Token("too"), Whitespace("\n", True),
                Token("look"), Whitespace(" "), comment_4, Whitespace(" "), Token("here"), Whitespace("\n", True),
                Token("next"), Whitespace(" "), comment_5, Whitespace(" "), Token("one"), Whitespace(" "), comment_6
            ]
            )
