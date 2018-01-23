#!/usr/bin/env python3
# coding: utf-8

import argparse
from pathlib import Path

from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter
from coraxml_utils.coralib import CoraToken
from coraxml_utils.modifier import add_tokenization_tags


if __name__ == "__main__":
    description = "Fügt einige extra Annotationen einer CorA-XML-Datei hinzu."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('infiles', nargs="+", help='Eingabedateien (XML)')
    parser.add_argument("-o", '--outpath', default=".",
                        help='Ausgabepfad')
    args, _ = parser.parse_known_args()

    MyImporter = create_importer("coraxml", dialect="anselm")
    MyExporter = create_exporter("coraxml")

    for filepath in args.infiles:

        print(f"processing {filepath}...")
        doc = MyImporter.import_from_file(filepath)

        for tok in filter(lambda x: isinstance(x, CoraToken), doc.tokens):
            # add tokenization tags
            tok = add_tokenization_tags(tok)

            # # add punc tags
            # tok = add_punc_tags(tok)

            # # TODO: für Anselm:  alle Satzzeichen auf $( setzen
            # tok = update_punct_pos(tok)

            # # split pos and morph attributes
            # tok = split_morph_from_pos(tok)

            # # rename lemmapos -> posLemma
            # tok = rename_lemmapos(tok)

            # # move lemma ID to its own attribute, if present
            # tok = split_lemma_id(tok)

            # # rename mod -> tok_mod, dipl -> tok_dipl
            # tok = rename_modipl(tok)

        output_xml = MyExporter.export(doc)

        with open(Path(args.outpath) / f"{doc.sigle}.xml", "wb") as outfile:
            output_xml.write(outfile, xml_declaration=True,
                             pretty_print=True, encoding='utf-8')

