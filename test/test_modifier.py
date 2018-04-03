import unittest

import json

import coraxml_utils.modifier
from coraxml_utils.character import *
from coraxml_utils.coralib import Trans

class TestUtils(unittest.TestCase):

    def test_trans_to_cora_json(self):

        my_parse = [
            TextChar('f', dipl_utf='f', anno_utf='f', anno_simple='f'),
            TextChar('o', dipl_utf='o', anno_utf='o', anno_simple='o'),
            TextChar('o', dipl_utf='o', anno_utf='o', anno_simple='o'),
            Hyphen('=', dipl_utf='='),
            Whitespace('\n'),
            TextChar('b', dipl_utf='b', anno_utf='b', anno_simple='b'),
            TextChar('a', dipl_utf='a', anno_utf='a', anno_simple='a'),
            TextChar('\\e', dipl_utf='ͤ', anno_utf='ͤ', anno_simple='e'),
            TextChar('r', dipl_utf='r', anno_utf='r', anno_simple='r'),
        ]
        my_parse[4].line_break=True
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

