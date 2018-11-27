import unittest

from coraxml_utils.parser import *


class LegacyTests(unittest.TestCase):

    def _create_rem_parse(test_string):

        tok = RemParser().parse(test_string)
        return tok

    def _test_tokenization_lengths(self, test_string, expected_dipl_number, expected_anno_number):

        tok = LegacyTests._create_rem_parse(test_string)
        tok_annos = tok.tokenize_anno()
        tok_dipls = tok.tokenize_dipl()

        self.assertEquals(len(tok_annos), expected_anno_number)
        self.assertEquals(len(tok_dipls), expected_dipl_number)

        return(tok_annos, tok_dipls)

    ## alinea
    def test_alinea(self):
        ### *C should be converted into // for simple and should be separated in anno

        tok_annos, _ = self._test_tokenization_lengths('*C*fJtem', 1, 2)

        self.assertEquals(
            tok_annos[0].simple(),
            '//'
        )
        self.assertEquals(
            tok_annos[1].simple(),
            'Jtem'
        )

    ## dash
    def test_dash_without_line_break(self):

        with self.assertRaises(ParseError):
            LegacyTests._create_rem_parse('different(=)text')

    def test_dash_with_line_break(self):

        self._test_tokenization_lengths('different(=)\ntext', 2, 1)

    ## dashpipe-check & dashpip-transform
    def test_dashpipe(self):

        self._test_tokenization_lengths('foo=|\nbar', 2, 2)

    def test_illegal_dashpipe(self):
        with self.assertRaises(ParseError):
            LegacyTests._create_rem_parse('foo|=\nbar')

        with self.assertRaises(ParseError):
            LegacyTests._create_rem_parse('foo(=)|\nbar')

        with self.assertRaises(ParseError):
            LegacyTests._create_rem_parse('foo|(=)\nbar')

    ## doubledash-illegible
    def test_doubledash_illegible(self):

        tok_annos, _ = self._test_tokenization_lengths('foo[=]\nbar', 2, 1)
        self.assertEquals(tok_annos[0].trans(), "foo[=]bar")

    def test_doubledash_and_before_illegible(self):

        tok_annos, _ = self._test_tokenization_lengths('[foo][=]\nbar', 2, 1)
        self.assertEquals(tok_annos[0].trans(), "[foo][=]bar")

    def test_doubledash_and_after_illegible(self):

        tok_annos, _ = self._test_tokenization_lengths('foo[=]\n[bar]', 2, 1)
        self.assertEquals(tok_annos[0].trans(), "foo[=][bar]")

    def test_doubledash_before_and_after_illegible(self):

        tok_annos, _ = self._test_tokenization_lengths('[[foo]][[=]]\n[bar]', 2, 1)
        self.assertEquals(tok_annos[0].trans(), "[[foo]][[=]][bar]")


    ## doubledash-syllabification
    def test_doubledash_syllabification(self):

        self._test_tokenization_lengths('Sig=\nmundt', 2, 1)
        self._test_tokenization_lengths('Sig(=)\nmundt', 2, 1)
        self._test_tokenization_lengths('Sig[=]\nmundt', 2, 1)
        self._test_tokenization_lengths('Sig[[=]]\nmundt', 2, 1)
        self._test_tokenization_lengths('Sig<=>\nmundt', 2, 1)
        self._test_tokenization_lengths('Sig<<=>>\nmundt', 2, 1)

class REMTests(unittest.TestCase):

    def _create_rem_parse(test_string):

        tok = RemParser().parse(test_string)
        return tok

    # bullets are not allowed
    def test_bullet(self):
        # REMTests._create_rem_parse("string\u00B7string")
        with self.assertRaises(ParseError) as cm:
            REMTests._create_rem_parse("string\u2219string")
