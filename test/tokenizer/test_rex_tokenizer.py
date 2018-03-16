import unittest
import logging

from coraxml_utils.tokenizer import *
from coraxml_utils.parser import ParseError


class RexTokenizerTests(unittest.TestCase):

    def setUp(self):

        self.tokenizer = tokenizer = RexTokenizer()


    ## legacy: comment-tags
    def test_nested_comments(self):
        with self.assertLogs(level=logging.ERROR):
            self.tokenizer.tokenize('+R Das ander Capittel der vor#rede(.)+K vor#rede(.): folgt Zeilenfüllung @K @R')

    def test_missing_whitespace_before_comment(self):
        with self.assertLogs(level=logging.ERROR):
            self.tokenizer.tokenize('noch ein+K test @K')

    def test_two_adjacent_comments(self):
        self.tokenizer.tokenize("zu Jn dann zu den mannen(.) +K mannen(.): folgt Schnörkel @K +K 20v,01: 'hagel machen' üdZ @K")

    ## legacy: dash
    def test_preedition_dash_with_linebreak(self):

        self.assertEquals(
            self.tokenizer.tokenize('different(=)\ntext'),
            [Token('different(=)\ntext')]
        )

    ## legacy: dashpipe-check
    def test_dash_with_linebreak(self):

        self.assertEquals(
            self.tokenizer.tokenize('foo=\nbar bla'),
            [Token('foo=\nbar'), Whitespace(' '), Token('bla')]
        )

    def test_dashpipe(self):

        self.assertEquals(
            self.tokenizer.tokenize('foo=|\nbar bla'),
            [Token('foo=|\nbar'), Whitespace(' '), Token('bla')]
        )

    ## legacy: doubledash-illegible
    def test_doubledash_illegible(self):

        self.assertEquals(
            self.tokenizer.tokenize("foo[=]\nbar\n[foo][=]\nbar\nfoo[=]\n[bar]\n[[foo]][[=]]\nbar"),
            [
                Token('foo[=]\nbar'), Whitespace("\n", True),
                Token('[foo][=]\nbar'), Whitespace("\n", True),
                Token('foo[=]\n[bar]'), Whitespace("\n", True),
                Token('[[foo]][[=]]\nbar')
            ]
        )

    def test_edition_numbering(self):


        comment_1 = Comment("E")
        comment_1.content.append("{5}")

        comment_2 = Comment("E")
        comment_2.content.append("{9}")

        comment_3 = Comment("E")
        comment_3.content.append("{1vf,2}")

        comment_4 = Comment("E")
        comment_4.content.append("{Kap.6,I}")

        comment_5 = Comment("E")
        comment_5.content.append("{Kap.6,I}")

        comment_6 = Comment("E")
        comment_6.content.append("{V.10,V}")

        self.assertEquals(
            self.tokenizer.tokenize("edition numbering {5} here\nhere {9} words\nhere {1vf,2} too\nlook {Kap.6,I} here\n{Str 7,X} another\nnext one {V.10,V}"),
            [
                Token("edition"), Whitespace(" "), Token("numbering"), Whitespace(" "), comment_1, Whitespace(" "), Token("here"), Whitespace("\n", True),
                Token("here"), Whitespace(" "), comment_2, Whitespace(" "), Token("words"), Whitespace("\n", True),
                Token("here"), Whitespace(" "), comment_3, Whitespace(" "), Token("too"), Whitespace("\n", True),
                Token("look"), Whitespace(" "), comment_4, Whitespace(" "), Token("here"), Whitespace("\n", True),
                comment_5, Whitespace(" "), Token("another"), Whitespace("\n", True),
                Token("next"), Whitespace(" "), Token("one"), Whitespace(" "), comment_6
            ]
            )


    def test_linebreak_whitespace(self):
        """ Test that tokenizer handles mixed whitespace situations appropriately
              for instance, when a line begins with a space character """
        test_string = "owe\n alsdkfj"
        mytokenizer = RexTokenizer()
        
        with self.assertLogs(level=logging.WARN):
            result = mytokenizer.tokenize(test_string)

        self.assertEquals(result, [Token("owe"), 
                                   Whitespace("\n", newline=True),
                                   Token("alsdkfj")])

