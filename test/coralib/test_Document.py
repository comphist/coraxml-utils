import unittest

from coraxml_utils.coralib import *
from coraxml_utils.parser import *

class DocumentTest(unittest.TestCase):

    def test_is_beginning_of_line(self):


        line_beginnings = [TokDipl(None) for i in range(4)]
        non_line_beginnings = [TokDipl(None) for i in range(4)]

        doc = Document('t', 'Test', {}, [
            Page('1', '', [
                Column([
                    Line('1', [
                        line_beginnings[0], non_line_beginnings[0]
                    ]),
                    Line('2', [
                        line_beginnings[1], non_line_beginnings[1]
                    ])
                ])
            ]),
            Page('2', '', [
                Column([
                    Line('1',[
                        line_beginnings[2], non_line_beginnings[2]
                    ]),
                    Line('2',[
                        line_beginnings[3], non_line_beginnings[3]
                    ])
                ])
            ])
        ], [])

        self.assertTrue(all([doc.is_beginning_of_line(dipl) for dipl in line_beginnings]))
        self.assertFalse(any([doc.is_beginning_of_line(dipl) for dipl in non_line_beginnings]))
