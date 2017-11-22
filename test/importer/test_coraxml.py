import unittest

from coraxml_utils.coralib import *
from coraxml_utils.importer import createCoraXMLImporter

try:
    from lxml import etree as ET
except ImportError:
    import xml.etree.ElementTree as ET

class CoraXMLImporterTest(unittest.TestCase):

    def test_importer_factory(self):

        with self.assertRaises(ValueError):
            createCoraXMLImporter('"some unknown dialect"')

    def test_dipl_from_xml(self):

        expected_dipl = TokDipl('t1_d1', 'test')

        dipl_element = ET.fromstring('<dipl id="t1_d1" trans="test" />')

        self.assertEquals(
            expected_dipl,
            createCoraXMLImporter()._createDiplToken(dipl_element)
        )
