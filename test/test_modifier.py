import unittest

import json

import coraxml_utils.modifier
from coraxml_utils.coralib import CoraToken
from coraxml_utils.character import *
from coraxml_utils.coralib import Trans
from coraxml_utils.parser import RefParser

class Test_add_punc_tests(unittest.TestCase):

    def test_preed_punc(self):
        token = CoraToken.from_parse(RefParser().parse('briffs(,)'))
        coraxml_utils.modifier.add_punc_tags(token)

        ## preed tokens have been removed ...
        self.assertEquals(len(token.tok_annos), 1)
        ## ... and added as annotation
        self.assertEquals(token.tok_annos[0].tags['punc'], '(,)')

    def test_preed_quotes_open(self):
        token = CoraToken.from_parse(RefParser().parse('(")owe'))
        coraxml_utils.modifier.add_punc_tags(token)

        ## preed tokens have been removed ...
        self.assertEquals(len(token.tok_annos), 1)
        ## ... and added as annotation
        self.assertEquals(token.tok_annos[0].tags['punc'], '(") |')

    def test_preed_quotes_open_and_punc(self):
        token = CoraToken.from_parse(RefParser().parse('(")owe(,)'))
        coraxml_utils.modifier.add_punc_tags(token)

        ## preed tokens have been removed ...
        self.assertEquals(len(token.tok_annos), 1)
        ## ... and added as annotation
        self.assertEquals(token.tok_annos[0].tags['punc'], '(") | (,)')

    def test_preed_quotes_close(self):

        token = CoraToken.from_parse(RefParser().parse('mir(?)(")'))
        coraxml_utils.modifier.add_punc_tags(token)

        ## preed tokens have been removed ...
        self.assertEquals(len(token.tok_annos), 1)
        ## ... and added as annotation
        self.assertEquals(token.tok_annos[0].tags['punc'], '(?) (")')


class TestUtils(unittest.TestCase):

    def test_trans_to_cora_json(self):

        my_parse = [
            TextChar('f', dipl_utf='f', anno_utf='f', anno_simple='f'),
            TextChar('o', dipl_utf='o', anno_utf='o', anno_simple='o'),
            TextChar('o', dipl_utf='o', anno_utf='o', anno_simple='o'),
            Hyphen('=', dipl_utf='='),
            LineBreak('\n'),
            TextChar('b', dipl_utf='b', anno_utf='b', anno_simple='b'),
            TextChar('a', dipl_utf='a', anno_utf='a', anno_simple='a'),
            TextChar('\\e', dipl_utf='ͤ', anno_utf='ͤ', anno_simple='e'),
            TextChar('r', dipl_utf='r', anno_utf='r', anno_simple='r'),
        ]
        # my_parse[4].line_break=True  ## required by object definition
        my_parse[4].dipl_bound=True

        self.assertEquals(
            json.loads(coraxml_utils.modifier.trans_to_cora_json(Trans(my_parse))),
            {
                'dipl_trans': ['foo=', 'ba\\er'],
                'dipl_utf': ['foo=', 'baͤr'],
                'dipl_breaks': [1, 0],
                'mod_trans': ['foo=ba\\er'],
                'mod_utf': ['foobaͤr'],
                'mod_ascii': ['foobaer'],
            }
        )

