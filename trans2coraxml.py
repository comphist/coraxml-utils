#!/usr/bin/env python3
# coding: utf-8

import argparse
import logging
logging.basicConfig(format='%(levelname)s: %(message)s')

from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter


__version__ = "2017.11.30"


if __name__ == "__main__":
    description = "Konvertiert eine Transkriptionsdatei ins CorA-XML-Format."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('infile',
                        help='Eingabedatei (Transkription)')
    parser.add_argument('outfile', nargs="?",
                        help='Ausgabedatei (XML)')
    # TODO: automatic tagging?
    parser.add_argument('-t', '--tag',
                        action='store_true',
                        default=False,
                        help='Automatisches Tagging der Eingabedatei')
    parser.add_argument('-p', '--par',
                        default='/usr/local/share/rftagger/lib/bonn.par',
                        help='Parameterdatei für den RFTagger (Default: %(default)s)')
    parser.add_argument('-g', '--genus',
                        action='store_true',
                        default=False,
                        help='Genusliste für ambige Nomina benutzen')
    parser.add_argument("-P", "--parser", choices=["rem", "anselm", "ref", "redi"],
                        default="ref", help="Token parser to use, default: %(default)s")
    args, _ = parser.parse_known_args()
    if _: logging.warn("Unknown args: %s", _)

    MyImporter = create_importer("trans", args.parser)
    MyExporter = create_exporter("coraxml", args.parser)

    doc = None
    with open(args.infile, "r", encoding="utf-8") as infile:
        doc = MyImporter.import_from_string(infile.read().replace("\ufeff", ""))

    if doc:
        output_xml = MyExporter.export(doc)

        if not args.outfile:
            args.outfile = doc.sigle + ".xml"

        with open(args.outfile, "wb") as outfile:
            output_xml.write(outfile, xml_declaration=True,
                             pretty_print=True, encoding='utf-8')

    else:
        print("document missing?")