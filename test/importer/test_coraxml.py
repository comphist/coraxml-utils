import unittest

from coraxml_utils.coralib import *
from coraxml_utils.parsed_token import PlainToken
from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter

try:
    from lxml import etree as ET
except ImportError:
    import xml.etree.ElementTree as ET

class CoraXMLImporterTest(unittest.TestCase):

    def test_dipl_from_xml(self):

        expected_dipl = TokDipl(PlainToken('test'), extid='t1_d1')
        dipl_element = ET.fromstring('<dipl id="t1_d1" trans="test" />')

        self.assertEquals(
            expected_dipl,
            create_importer('coraxml')._create_dipl_token(dipl_element)
        )

    def test_anno_from_xml(self):

        expected_anno = TokAnno(
            PlainToken('priuilegien'),
            tags={'lemma': 'privileg', 'pos': 'NA', 'morph': 'Fem.Dat.Pl', 'boundary': 'Satz'},
            flags=set(['lemma verified', 'boundary']),
            checked=True, extid='t1_m1'
        )
        anno_element = ET.fromstring('<mod id="t1_m1" trans="priuilegien" utf="priuilegien" ascii="priuilegien" checked="y"><lemma tag="privileg"/><pos tag="NA"/><boundary tag="Satz"/><morph tag="Fem.Dat.Pl"/><cora-flag name="lemma verified"/><cora-flag name="boundary"/></mod>')

        self.assertEquals(
            expected_anno,
            create_importer('coraxml')._create_anno_token(anno_element)
        )


    def test_anno_with_doubled_tags(self):

        anno_element = ET.fromstring('<mod id="t1_m1" trans="priuilegien" utf="priuilegien" ascii="priuilegien" checked="y"><pos tag="NA"/><pos tag="NA"/></mod>')

        with self.assertLogs(None, 'WARN'):
            create_importer('coraxml')._create_anno_token(anno_element)

    def test_cora_token_from_xml(self):

        expected_token = CoraToken(
            PlainToken('test|case'),
            [TokDipl(PlainToken('test|case'), extid='t1_d1')],
            [TokAnno(PlainToken('test|'), extid='t1_m1', checked=True), TokAnno(PlainToken('case'), extid='t1_m2')],
            extid='t1'
        )
        token_element = ET.fromstring('<token id="t1" trans="test|case"><dipl id="t1_d1" trans="test|case" /><mod id="t1_m1" trans="test|" checked="y" /><mod id="t1_m2" trans="case" /></token>')

        self.assertEquals(
            expected_token,
            create_importer('coraxml')._create_cora_token(token_element)
        )

class CoraXMLExporterTest(unittest.TestCase):

    pass
