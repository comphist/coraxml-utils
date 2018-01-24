#!/usr/bin/env python3
# coding: utf-8

import argparse
from pathlib import Path

from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter
from coraxml_utils.coralib import CoraToken
from coraxml_utils.modifier import add_tokenization_tags, update_punct_pos


if __name__ == "__main__":
    description = "Fügt einige extra Annotationen einer CorA-XML-Datei hinzu."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('infiles', nargs="+", help='Eingabedateien (XML)')
    parser.add_argument("-o", '--outpath', default=".",
                        help='Ausgabepfad')
    args, _ = parser.parse_known_args()

    # name mod -> tok_anno, dipl -> tok_dipl
    MyImporter = create_importer("coraxml", dialect="anselm")
    MyExporter = create_exporter("coraxml", options={
        'dipl_tag_name': 'tok_dipl',
        'anno_tag_name': 'tok_anno',
    })

    for filepath in args.infiles:

        print(f"processing {filepath}...")
        doc = MyImporter.import_from_file(filepath)

        for tok in filter(lambda x: isinstance(x, CoraToken), doc.tokens):

            # remove comment and boundary
            for tok_anno in tok.tok_annos:
                tok_anno.tags.pop('comment', None)
                tok_anno.tags.pop('boundary', None)
                tok_anno.flags.discard('boundary')

            # add tokenization tags
            tok = add_tokenization_tags(tok)

            # add punc tags
            # ANSELM: as yet no pre-edition punctuation 
            # (and therefore no sent bounds discernible)
            # tok = add_punc_tags(tok)

            # alle Satzzeichen (type = p) auf $( setzen (wenn noch nichts gesetzt)
            tok = update_punct_pos(tok)



        output_xml = MyExporter.export(doc)

        with open(Path(args.outpath) / f"{doc.sigle}.xml", "wb") as outfile:
            output_xml.write(outfile, xml_declaration=True,
                             pretty_print=True, encoding='utf-8')

