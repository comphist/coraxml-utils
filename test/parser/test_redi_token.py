import unittest

from coraxml_utils.parser import *

class ParserTest(unittest.TestCase):

    def _create_redi_parse(test_string):

        tok = RediParser().parse(test_string)
        return tok

    def test_allowed_characters(self):

        try:
            ParserTest._create_redi_parse('(")mensch')
        except:
            self.fail('(")mensch should be a valid transcription')


