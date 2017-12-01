import unittest

from coraxml_utils.importer import create_importer

class ImporterFactoryTest(unittest.TestCase):

    def test_unsupported_file_format(self):

        with self.assertRaises(ValueError):
            create_importer('"some unknown format"')

    def test_coraxml_unsupported_dialect(self):

        with self.assertRaises(ValueError):
            create_importer('coraxml', '"some unknown dialect"')
