#!/usr/bin/env python3
# coding: utf-8

import argparse
import json

from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter

if __name__ == "__main__":
    description = "Konvertiert eine CorA-XML-Datei ins GATE JSON-Format."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("infile", help="Eingabedatei (XML)")
    parser.add_argument("outfile", nargs="?", help="Ausgabedatei (JSON)")
    parser.add_argument(
        "-P",
        "--parser",
        choices=["rem", "anselm", "ref", "redi"],
        default="ref",
        help="Token parser to use, default: %(default)s",
    )
    args, _ = parser.parse_known_args()

    MyImporter = create_importer("coraxml", args.parser)
    MyExporter = create_exporter("gatejson")

    doc = MyImporter.import_from_file(args.infile)
    json_doc = MyExporter.export(doc)
    json.dump(json_doc, open(args.outfile, "w"))
