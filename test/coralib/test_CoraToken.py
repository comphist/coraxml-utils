import unittest

from coraxml_utils.coralib import *
from coraxml_utils.parsed_token import *

class CoraTokenTest(unittest.TestCase):

    def test_tokenalignment_multiple_dipls(self):

        expected_alignment = [
            {'type': 'token_begin', 'dipl_id': 'd1', 'anno_id': 'a1'},
            {'trans': 't', 'simple': 't', 'utf': 't', 'type': 'w'},
            {'trans': 'e', 'simple': 'e', 'utf': 'e', 'type': 'w'},
            {'trans': 's', 'simple': 's', 'utf': 's', 'type': 'w'},
            {'trans': 't', 'simple': 't', 'utf': 't', 'type': 'w'},
            {'type': 'token_end', 'dipl_id': 'd1'},
            {'type': 'token_begin', 'dipl_id': 'd2'},
            {'trans': 'c', 'simple': 'c', 'utf': 'c', 'type': 'w'},
            {'trans': 'a', 'simple': 'a', 'utf': 'a', 'type': 'w'},
            {'trans': 's', 'simple': 's', 'utf': 's', 'type': 'w'},
            {'trans': 'e', 'simple': 'e', 'utf': 'e', 'type': 'w'},
            {'type': 'token_end', 'dipl_id': 'd2', 'anno_id': 'a1'},
        ]
        dipl_list = [TokDipl(PlainToken('test')), TokDipl(PlainToken('case'))]
        dipl_list[0]._id = 'd1'
        dipl_list[1]._id = 'd2'
        anno_list = [TokAnno(PlainToken('testcase'))]
        anno_list[0]._id = 'a1'
        alignment = CoraToken(
            PlainToken('testcase'),
            dipl_list,
            anno_list
        ).get_aligned_dipls_and_annos()

        self.assertEquals(
            expected_alignment,
            alignment
        )

    def test_tokenalignment_multiple_annos(self):

        expected_alignment = [
            {'type': 'token_begin', 'dipl_id': 'd1', 'anno_id': 'a1'},
            {'trans': 't', 'simple': 't', 'utf': 't', 'type': 'w'},
            {'trans': 'e', 'simple': 'e', 'utf': 'e', 'type': 'w'},
            {'trans': 's', 'simple': 's', 'utf': 's', 'type': 'w'},
            {'trans': 't', 'simple': 't', 'utf': 't', 'type': 'w'},
            {'type': 'token_end', 'anno_id': 'a1'},
            {'type': 'token_begin', 'anno_id': 'a2'},
            {'trans': 'c', 'simple': 'c', 'utf': 'c', 'type': 'w'},
            {'trans': 'a', 'simple': 'a', 'utf': 'a', 'type': 'w'},
            {'trans': 's', 'simple': 's', 'utf': 's', 'type': 'w'},
            {'trans': 'e', 'simple': 'e', 'utf': 'e', 'type': 'w'},
            {'type': 'token_end', 'dipl_id': 'd1', 'anno_id': 'a2'},
        ]
        dipl_list = [TokDipl(PlainToken('testcase'))]
        dipl_list[0]._id = 'd1'
        anno_list = [TokAnno(PlainToken('test')), TokAnno(PlainToken('case'))]
        anno_list[0]._id = 'a1'
        anno_list[1]._id = 'a2'
        alignment = CoraToken(
            PlainToken('testcase'),
            dipl_list,
            anno_list
        ).get_aligned_dipls_and_annos()

        self.assertEquals(
            expected_alignment,
            alignment
        )

    def test_tokenalignment_only_dipls(self):

        expected_alignment = [
            {'type': 'token_begin', 'dipl_id': 'd1'},
            {'trans': 't', 'simple': 't', 'utf': 't', 'type': 'w'},
            {'trans': 'e', 'simple': 'e', 'utf': 'e', 'type': 'w'},
            {'trans': 's', 'simple': 's', 'utf': 's', 'type': 'w'},
            {'trans': 't', 'simple': 't', 'utf': 't', 'type': 'w'},
            {'type': 'token_end', 'dipl_id': 'd1'},
            {'type': 'token_begin', 'dipl_id': 'd2'},
            {'trans': 'c', 'simple': 'c', 'utf': 'c', 'type': 'w'},
            {'trans': 'a', 'simple': 'a', 'utf': 'a', 'type': 'w'},
            {'trans': 's', 'simple': 's', 'utf': 's', 'type': 'w'},
            {'trans': 'e', 'simple': 'e', 'utf': 'e', 'type': 'w'},
            {'type': 'token_end', 'dipl_id': 'd2'},
        ]
        dipl_list = [TokDipl(PlainToken('test')), TokDipl(PlainToken('case'))]
        dipl_list[0]._id = 'd1'
        dipl_list[1]._id = 'd2'
        anno_list = []
        alignment = CoraToken(
            PlainToken('testcase'),
            dipl_list,
            anno_list
        ).get_aligned_dipls_and_annos()

        self.assertEquals(
            expected_alignment,
            alignment
        )

    def test_tokenalignment_unalignable(self):

        ## dipl contains character not in annos
        with self.assertRaises(ValueError):
            CoraToken(
                PlainToken('testcase'),
                [TokDipl(PlainToken('testecase'))],
                [TokAnno(PlainToken('test')), TokAnno(PlainToken('case'))]
            ).get_aligned_dipls_and_annos()


        ## annos is shorter than dipls
        with self.assertRaises(ValueError):
            CoraToken(
                PlainToken('testcase'),
                [TokDipl(PlainToken('testcase'))],
                [TokAnno(PlainToken('test'))]
            ).get_aligned_dipls_and_annos()
