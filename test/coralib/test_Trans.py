import unittest

from coraxml_utils.parser import *
from coraxml_utils.coralib import Trans

class TransTest(unittest.TestCase):

    def test_parse_with_tokenization_multiple_dipls(self):

        parse_without_boundaries = [
            {'trans': 't', 'anno_simple': 't', 'dipl_utf': 't', 'anno_utf': 't', 'type': 'w'},
            {'trans': 'e', 'anno_simple': 'e', 'dipl_utf': 'e', 'anno_utf': 'e', 'type': 'w'},
            {'trans': 's', 'anno_simple': 's', 'dipl_utf': 's', 'anno_utf': 's', 'type': 'w'},
            {'trans': 't', 'anno_simple': 't', 'dipl_utf': 't', 'anno_utf': 't', 'type': 'w'},
            {'trans': '#', 'anno_simple': '', 'dipl_utf': '', 'anno_utf': '', 'type': 'spl'},
            {'trans': 'c', 'anno_simple': 'c', 'dipl_utf': 'c', 'anno_utf': 'c', 'type': 'w'},
            {'trans': 'a', 'anno_simple': 'a', 'dipl_utf': 'a', 'anno_utf': 'a', 'type': 'w'},
            {'trans': 's', 'anno_simple': 's', 'dipl_utf': 's', 'anno_utf': 's', 'type': 'w'},
            {'trans': 'e', 'anno_simple': 'e', 'dipl_utf': 'e', 'anno_utf': 'e', 'type': 'w'},
        ]
        dipl_boundaries = [4]

        expected_alignment = [
            {'trans': 't', 'anno_simple': 't', 'dipl_utf': 't', 'anno_utf': 't', 'type': 'w'},
            {'trans': 'e', 'anno_simple': 'e', 'dipl_utf': 'e', 'anno_utf': 'e', 'type': 'w'},
            {'trans': 's', 'anno_simple': 's', 'dipl_utf': 's', 'anno_utf': 's', 'type': 'w'},
            {'trans': 't', 'anno_simple': 't', 'dipl_utf': 't', 'anno_utf': 't', 'type': 'w'},
            {'trans': '#', 'anno_simple': '', 'dipl_utf': '', 'anno_utf': '', 'type': 'spl', 'dipl_boundary': True},
            {'trans': 'c', 'anno_simple': 'c', 'dipl_utf': 'c', 'anno_utf': 'c', 'type': 'w'},
            {'trans': 'a', 'anno_simple': 'a', 'dipl_utf': 'a', 'anno_utf': 'a', 'type': 'w'},
            {'trans': 's', 'anno_simple': 's', 'dipl_utf': 's', 'anno_utf': 's', 'type': 'w'},
            {'trans': 'e', 'anno_simple': 'e', 'dipl_utf': 'e', 'anno_utf': 'e', 'type': 'w'},
        ]
        alignment = Trans(parse_without_boundaries, dipl_splits=dipl_boundaries).get_parse_with_tokenization()

        self.assertEquals(
            expected_alignment,
            alignment
        )


    def test_parse_with_tokenization_mulitple_annos(self):

        parse_without_boundaries = [
            {'trans': 't', 'anno_simple': 't', 'dipl_utf': 't', 'anno_utf': 't', 'type': 'w'},
            {'trans': 'e', 'anno_simple': 'e', 'dipl_utf': 'e', 'anno_utf': 'e', 'type': 'w'},
            {'trans': 's', 'anno_simple': 's', 'dipl_utf': 's', 'anno_utf': 's', 'type': 'w'},
            {'trans': 't', 'anno_simple': 't', 'dipl_utf': 't', 'anno_utf': 't', 'type': 'w'},
            {'trans': '|', 'anno_simple': '', 'dipl_utf': '', 'anno_utf': '', 'type': 'spl'},
            {'trans': 'c', 'anno_simple': 'c', 'dipl_utf': 'c', 'anno_utf': 'c', 'type': 'w'},
            {'trans': 'a', 'anno_simple': 'a', 'dipl_utf': 'a', 'anno_utf': 'a', 'type': 'w'},
            {'trans': 's', 'anno_simple': 's', 'dipl_utf': 's', 'anno_utf': 's', 'type': 'w'},
            {'trans': 'e', 'anno_simple': 'e', 'dipl_utf': 'e', 'anno_utf': 'e', 'type': 'w'},
        ]
        anno_boundaries = [4]

        expected_alignment = [
            {'trans': 't', 'anno_simple': 't', 'dipl_utf': 't', 'anno_utf': 't', 'type': 'w'},
            {'trans': 'e', 'anno_simple': 'e', 'dipl_utf': 'e', 'anno_utf': 'e', 'type': 'w'},
            {'trans': 's', 'anno_simple': 's', 'dipl_utf': 's', 'anno_utf': 's', 'type': 'w'},
            {'trans': 't', 'anno_simple': 't', 'dipl_utf': 't', 'anno_utf': 't', 'type': 'w'},
            {'trans': '|', 'anno_simple': '', 'dipl_utf': '', 'anno_utf': '', 'type': 'spl', 'anno_boundary': True},
            {'trans': 'c', 'anno_simple': 'c', 'dipl_utf': 'c', 'anno_utf': 'c', 'type': 'w'},
            {'trans': 'a', 'anno_simple': 'a', 'dipl_utf': 'a', 'anno_utf': 'a', 'type': 'w'},
            {'trans': 's', 'anno_simple': 's', 'dipl_utf': 's', 'anno_utf': 's', 'type': 'w'},
            {'trans': 'e', 'anno_simple': 'e', 'dipl_utf': 'e', 'anno_utf': 'e', 'type': 'w'},
        ]
        alignment = Trans(parse_without_boundaries, anno_splits=anno_boundaries).get_parse_with_tokenization()

        self.assertEquals(
            expected_alignment,
            alignment
        )
