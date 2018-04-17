import unittest

from coraxml_utils.coralib import *
from coraxml_utils.parser import *
from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter

from lxml import etree as ET

class CoraXMLImporterTest(unittest.TestCase):

    def test_dipl_from_xml(self):

        expected_dipl = TokDipl(PlainParser().parse('test', output_type="dipl"), extid='t1_d1')
        dipl_element = ET.fromstring('<dipl id="t1_d1" trans="test" />')

        self.assertEquals(
            expected_dipl,
            create_importer('coraxml')._create_dipl_token(dipl_element, PlainParser().parse('test', output_type="dipl"))
        )

    def test_anno_from_xml(self):

        expected_anno = TokAnno(
            PlainParser().parse('priuilegien', output_type="anno"),
            tags={'lemma': 'privileg', 'pos': 'NA', 'morph': 'Fem.Dat.Pl', 'boundary': 'Satz'},
            flags=set(['lemma verified', 'boundary']),
            checked=True, extid='t1_m1'
        )
        anno_element = ET.fromstring('<mod id="t1_m1" trans="priuilegien" utf="priuilegien" ascii="priuilegien" checked="y"><lemma tag="privileg"/><pos tag="NA"/><boundary tag="Satz"/><morph tag="Fem.Dat.Pl"/><cora-flag name="lemma verified"/><cora-flag name="boundary"/></mod>')

        self.assertEquals(
            expected_anno,
            create_importer('coraxml')._create_anno_token(anno_element, PlainParser().parse('priuilegien', output_type="anno"))
        )

    def test_anno_from_xml_with_trans_token_mismatch(self):

        anno_element = ET.fromstring(
            """<token id="t1324" trans="her#aws">
                 <dipl id="t1324_d1" trans="her#aws" utf="heraws"/>
                 <mod id="t1324_m1" trans="her#aws" utf="heraws" ascii="heraws" checked="y" />
               </token>""")

        ## strict mode: error
        with self.assertLogs(None, 'ERROR'):
            create_importer('coraxml', 'anselm')._create_cora_token(anno_element, set())

        ## nonstrict mode: token is created as given by XML
        expected_token = CoraToken(
            AnselmParser().parse('her#aws'),
            [TokDipl(AnselmParser().parse('her#aws', output_type="dipl"), extid='t1324_d1')],
            [TokAnno(AnselmParser().parse('her#aws', output_type="anno"), extid='t1324_m1', checked=True)],
            extid='t1324'
        )
        self.assertEquals(
            expected_token,
            create_importer('coraxml', 'anselm', strict=False)._create_cora_token(anno_element, set())
        )


    def test_anno_from_xml_with_transcription_mismatch(self):

        anno_element = ET.fromstring(
            """<token id="t924" trans="hin#cz&#xFC;|hin(.)">
                 <dipl id="t924_d1" trans="hin#cz&#xFC;|" utf="hincz&#xFC;"/>
                 <dipl id="t924_d2" trans="hin" utf="hin"/>
                 <mod id="t924_m1" trans="hin#cz&#xFC;|" utf="hincz&#xFC;" ascii="hincz&#xFC;" checked="y" />
                 <mod id="t924_m2" trans="hin" utf="hin" ascii="hin" checked="y" />
                 <mod id="t924_m3" trans="(.)" utf="." ascii="." checked="y" />
               </token>""")

        ## strict mode: error
        with self.assertLogs(None, 'ERROR'):
            create_importer('coraxml', 'anselm')._create_cora_token(anno_element, set())

        ## nonstrict mode: token is created as given by XML
        expected_token = CoraToken(
            AnselmParser().parse('hin#czü|hin'),
            [TokDipl(AnselmParser().parse('hin#czü|', output_type="dipl"), extid='t924_d1'), TokDipl(AnselmParser().parse('hin', output_type="dipl"), extid='t924_d2')],
            [TokAnno(AnselmParser().parse('hin#czü|', output_type="anno"), extid='t924_m1', checked=True), TokAnno(AnselmParser().parse('hin', output_type="anno"), extid='t924_m2', checked=True), TokAnno(AnselmParser().parse('(.)', output_type="anno"), extid='t924_m3', checked=True)
            ],
            extid='t924'
        )
        self.assertEquals(
            expected_token,
            create_importer('coraxml', 'anselm', strict=False)._create_cora_token(anno_element, set())
        )

    def test_anno_with_doubled_tags(self):

        anno_element = ET.fromstring('<mod id="t1_m1" trans="priuilegien" utf="priuilegien" ascii="priuilegien" checked="y"><pos tag="NA"/><pos tag="NA"/></mod>')

        with self.assertLogs(None, 'WARN'):
            create_importer('coraxml')._create_anno_token(anno_element, PlainParser().parse('priuilegien', output_type="dipl"))

    def test_cora_token_from_xml(self):

        expected_token = CoraToken(
            PlainParser().parse('test|case'),
            [TokDipl(PlainParser().parse('test|case', output_type="dipl"), extid='t1_d1')],
            [TokAnno(PlainParser().parse('test|', output_type="anno"), extid='t1_m1', checked=True), TokAnno(PlainParser().parse('case', output_type="anno"), extid='t1_m2')],
            extid='t1'
        )
        token_element = ET.fromstring('<token id="t1" trans="test|case"><dipl id="t1_d1" trans="test|case" /><mod id="t1_m1" trans="test|" checked="y" /><mod id="t1_m2" trans="case" /></token>')

        self.assertEquals(
            expected_token,
            create_importer('coraxml')._create_cora_token(token_element, set())
        )

