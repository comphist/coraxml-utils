#!/usr/bin/env python3
# coding: utf-8

import argparse
from lxml import etree

from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter

if __name__ == "__main__":
    description = "Konvertiert eine CorA-XML-Datei ins TEI-Format."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("infile", help="Eingabedatei (XML)")
    parser.add_argument("outfile", nargs="?", help="Ausgabedatei (XML)")
    parser.add_argument(
        "-P",
        "--parser",
        choices=["rem", "anselm", "ref", "redi"],
        default="ref",
        help="Token parser to use, default: %(default)s",
    )
    args, _ = parser.parse_known_args()

    MyImporter = create_importer("coraxml", args.parser)
    MyExporter = create_exporter("tei")

    doc = MyImporter.import_from_file(args.infile)
    tei_doc = MyExporter.export(doc)
    ausgabe = etree.tounicode(tei_doc)
    ausgabe = (
        ausgabe.replace("<lb ", "\n<lb ")
        .replace("<pb ", "\n<pb ")
        .replace("<space ", " <space ")
    )
    print(ausgabe, file=open(args.outfile, "w", encoding="utf-8"))
