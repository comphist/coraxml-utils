#!/usr/bin/env python3
# coding: utf-8

import argparse
from pathlib import Path

from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter
from coraxml_utils.coralib import CoraToken
from coraxml_utils.modifier import add_tokenization_tags, update_punct_pos, fill_annotation_column, change_tags


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

        print("processing %s..." % filepath)
        doc = MyImporter.import_from_file(filepath)

        for tok in filter(lambda x: isinstance(x, CoraToken), doc.tokens):

            for tok_anno in tok.tok_annos:
                # remove comment and boundary
                tok_anno.tags.pop('comment', None)
                tok_anno.tags.pop('boundary', None)
                tok_anno.flags.discard('boundary')

                # add "--" if morph is not set
                fill_annotation_column(tok_anno, 'morph')
                # set norm_broad to norm if it is not set
                if 'norm' in tok_anno.tags:
                    fill_annotation_column(tok_anno, 'norm_broad', tok_anno.tags['norm'])

                # rename norm_type-tags
                change_tags(tok_anno, 'norm_type', {
                    'f': 'inflection',
                    's': 'semantic',
                    'x': 'extinct'
                })

            # add tokenization tags
            add_tokenization_tags(tok)

            # add punc tags
            # ANSELM: as yet no pre-edition punctuation 
            # (and therefore no sent bounds discernible)
            # tok = add_punc_tags(tok)

            # alle Satzzeichen (type = p) auf $( setzen (wenn noch nichts gesetzt)
            update_punct_pos(tok)



        output_xml = MyExporter.export(doc)
        outfilepath = str(Path(args.outpath) / (doc.sigle + ".xml"))
        with open(outfilepath, "wb") as outfile:
            output_xml.write(outfile, xml_declaration=True,
                             pretty_print=True, encoding='utf-8')

