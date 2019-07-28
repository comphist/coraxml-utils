import unittest

from coraxml_utils.parser import *
from coraxml_utils.coralib import Trans

class AnselmParserTest(unittest.TestCase):

    def _create_anselm_parse(test_string):
        tok = AnselmParser().parse(test_string)
        return tok

    def test_pro_error(self):
        """Make sure that not all p's are simplified to pro"""

        tok = AnselmParserTest._create_anselm_parse("zer$panten")
        self.assertEquals(tok.tokenize_anno()[0].simple(), "zerspanten")

        tok = AnselmParserTest._create_anselm_parse("enpei$$en")
        self.assertEquals(tok.tokenize_anno()[0].simple(), "enpeissen")

    def test_strikethrough_tokenization(self):
        """Make sure that no mod-tokens are created if whole token is marked as strike through."""

        tok = AnselmParserTest._create_anselm_parse("*[$we$ter*]")
        self.assertEquals(len(tok.tokenize_anno()), 0)

    def test_line_split_preedition(self):
        """
        Test handling of (=), should:
        - only occur at line end
        - result in 2 dipls, 1 mod
        - be tagged as UL
        - not co-occur with M* symbols
        - not occur multiple times in succession
        """

        tok = AnselmParserTest._create_anselm_parse("hymel(=)\nreich")
        self.assertEquals(len(tok.tokenize_dipl()), 2)

        # co-occurence with `|` should result in an error
        with self.assertRaises(ParseError):
            AnselmParserTest._create_anselm_parse("hymel(=)|reich")

        with self.assertRaises(ParseError):
            AnselmParserTest._create_anselm_parse("hymel|(=)reich")

    def test_multiverbation(self):
        tok = AnselmParserTest._create_anselm_parse("dy\:|es")
        self.assertEquals(len(tok.tokenize_dipl()), 1)

    def test_dot_above_split(self):
        """Dot above (\.) should not be a separate anno token"""

        tok = AnselmParserTest._create_anselm_parse("fraw\.")
        self.assertEquals(len(tok.tokenize_anno()), 1)

    def test_illegible_token(self):

        tok = AnselmParserTest._create_anselm_parse("<...>")
        self.assertEquals(len(tok.tokenize_anno()), 1)
        self.assertEquals(len(tok.tokenize_dipl()), 1)

    def test_single_tokenization(self):

        tok = AnselmParserTest._create_anselm_parse("tok#en.iza|tion%....")
        self.assertEquals([x.simple() for x in tok.tokenize_anno()],
                          ["token.iza", "tion", ".", "..."])

        self.assertEquals([str(x) for x in tok.tokenize_dipl() if x],
                          ["tok#", "en.iza|tion%...."])
    
    def test_multiline_tokenization(self):
        tok = AnselmParserTest._create_anselm_parse("token(=)\nizat=\nion.")
        self.assertEquals([x.simple() for x in tok.tokenize_anno()],
                          ["tokenization", "."])
        self.assertEquals([str(x) for x in tok.tokenize_dipl() if x],
                          ["token(=)", "izat=", "ion."])

    def test_hochstellung(self):
        tok = AnselmParserTest._create_anselm_parse("de%$")
        self.assertIsInstance(tok, Trans)

    # TODO should be allowed
    def test_brackets_lineend(self):
        with self.assertRaises(ParseError):
            AnselmParserTest._create_anselm_parse("*[wi(=)\nder*]")
    
    # TODO should be allowed
    # TODO make sure this gets tokenized
    def test_legalbrackets_lineend(self):
        #  should be '[[ge]](=)\ntan'
        with self.assertRaises(ParseError):
            AnselmParser().parse("[[ge(=)]]\ntan")

    def test_tokenize_atbracket(self):
        tok = AnselmParser().parse("er$<ch>(=)<ain>")
        self.assertEqual([str(x) for x in tok.tokenize_dipl()],
                         ["er$<ch>(=)", "<ain>"])
        
    def test_abbreviations(self):
        tok = AnselmParser().parse("h<.$.>")
        self.assertIsInstance(tok, Trans)

        self.assertEqual(tok.tokenize_anno()[0].simple(), "h.s.")

    def test_unleserlichpunct(self):
        res = [x.simple() for x in AnselmParser().parse("eyn<s></>(.)").tokenize_anno()]
        self.assertEqual(res, ["eyns", "/", "(.)"])


    def test_majuskels(self):
        tok = AnselmParser().parse("*{D*}iz")
        self.assertEqual(tok.parse, [Majuscule("*{D*}", "", 
                                     anno_simple="D", anno_utf="D", dipl_utf="D"), 
                                     TextChar("i", anno_simple="i", anno_utf="i", dipl_utf="i"), 
                                     TextChar("z", anno_simple="z", anno_utf="z", dipl_utf="z")])

    def test_fromedition(self):
        tok = AnselmParser().parse("$wer[t]").tokenize_dipl()[0]
        self.assertEqual(tok.utf(), "ſwer[...]")

    def test_editorcompleted(self):
        tok = AnselmParser().parse("$wer[[t]]").tokenize_dipl()[0]
        self.assertEqual(tok.utf(), "ſwer[...]")

    def test_lacuna(self):
        tok = AnselmParser().parse("foo<<...>>").tokenize_anno()[0]
        self.assertEqual(tok.utf(), "foo[...]")

    def test_period_grouping(self):
        tok = AnselmParser().parse("foo...").tokenize_anno()
        self.assertEqual(len(tok), 2)

    def test_unleserlich_chars(self):
        tok = AnselmParser().parse("test[..]")
        self.assertEqual(" ".join(x.simple() for x in tok.tokenize_anno()),
                         "test..")

    def test_unleserlich_punct(self):
        tok = AnselmParser().parse("test[.]")
        self.assertEqual(len(tok.tokenize_anno()), 2)

    def test_from_edition_punct(self):
        tok = AnselmParser().parse("test<.>")
        self.assertEqual(len(tok.tokenize_anno()), 2)

    def test_virgel(self):
        tok = AnselmParser().parse("meinenn/")
        self.assertEqual(len(tok.tokenize_anno()), 2)

    def test_inner_word_virgel(self):
        ## don't separate virgel after linebreak and joiner
        tok = AnselmParser().parse("mei(=)\n/nenn")
        self.assertEqual(len(tok.tokenize_anno()), 1)

    def test_multiline_tokenization_anno(self):
        ## should ignore missing linebreak when type is anno

        tok = AnselmParser().parse("mei(=)/nenn", output_type='anno')


    def test_abbreviations(self):
        ## . should not be separated

        tok = AnselmParser().parse(".xij.")
        self.assertEqual(len(tok.tokenize_anno()), 1)

    def test_punct_after_bracket(self):
        ## %. should be separated

        tok = AnselmParser().parse("oli<ueti>%.")
        self.assertEqual(len(tok.tokenize_anno()), 2)

    def test_punct_before_joiner(self):
        ## . should not be separated

        tok = AnselmParser().parse("dz.(=)\n$elbe\-")
        self.assertEqual(len(tok.tokenize_anno()), 1)

    def test_preed_quotes_tokenization(self):
        ## (") at the beginning should be separated

        tok = AnselmParser().parse("(\")owe")
        ## two tokens ...
        self.assertEqual(len(tok.tokenize_anno()), 2)
        ## ... with the correct content
        self.assertEqual(tok.tokenize_anno()[0].trans(), "(\")")
        self.assertEqual(tok.tokenize_anno()[1].trans(), "owe")


    def test_preed_quotes_tokenization_only_one_character(self):
        ## (") at the beginning should be separated

        tok = AnselmParser().parse("(\")o")
        ## two tokens ...
        self.assertEqual(len(tok.tokenize_anno()), 2)
        ## ... with the correct content
        self.assertEqual(tok.tokenize_anno()[0].trans(), "(\")")
        self.assertEqual(tok.tokenize_anno()[1].trans(), "o")

    def test_punct_and_preed_punct(self):

        tok = AnselmParser().parse("wi$$e[n].(.)")
        ## 3 tokens ...
        self.assertEqual(len(tok.tokenize_anno()), 3)
        ## ... with the correct content
        self.assertEqual(tok.tokenize_anno()[0].trans(), "wi$$e[n]")
        self.assertEqual(tok.tokenize_anno()[1].trans(), ".")
        self.assertEqual(tok.tokenize_anno()[2].trans(), "(.)")

