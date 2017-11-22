import unittest

from coraxml_utils.coralib import *
from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter

try:
    from lxml import etree as ET
except ImportError:
    import xml.etree.ElementTree as ET

class CoraXMLImporterTest(unittest.TestCase):

    def test_dipl_from_xml(self):

        expected_dipl = TokDipl('t1_d1', 'test')
        dipl_element = ET.fromstring('<dipl id="t1_d1" trans="test" />')

        self.assertEquals(
            expected_dipl,
            create_importer('CorA-XML')._create_dipl_token(dipl_element)
        )

    def test_anno_from_xml(self):

        expected_anno = TokAnno(
            't1_m1', 'priuilegien',
            {'lemma': 'privileg', 'pos': 'NA', 'morph': 'Fem.Dat.Pl', 'boundary': 'Satz'},
            set(['lemma verified', 'boundary']),
            True
        )
        anno_element = ET.fromstring('<mod id="t1_m1" trans="priuilegien" utf="priuilegien" ascii="priuilegien" checked="y"><lemma tag="privileg"/><pos tag="NA"/><boundary tag="Satz"/><morph tag="Fem.Dat.Pl"/><cora-flag name="lemma verified"/><cora-flag name="boundary"/></mod>')

        self.assertEquals(
            expected_anno,
            create_importer('CorA-XML')._create_anno_token(anno_element)
        )


    def test_anno_with_doubled_tags(self):

        anno_element = ET.fromstring('<mod id="t1_m1" trans="priuilegien" utf="priuilegien" ascii="priuilegien" checked="y"><pos tag="NA"/><pos tag="NA"/></mod>')

        with self.assertLogs(None, 'WARN'):
            create_importer('CorA-XML')._create_anno_token(anno_element)


class CoraXMLExporterTest(unittest.TestCase):

    pass