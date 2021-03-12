import logging
import json

import click
from lxml import etree

import coraxml_utils.parser
from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter


@click.group()
def main():
    pass


@main.command()
@click.argument("infile", type=click.File("r"))
@click.option(
    "-f",
    "--from",
    "from_",
    type=click.Choice(["coraxml", "bonnxml", "trans"]),
    default="trans",
    show_default=True,
    help="Format of the input.",
)
@click.option(
    "-t",
    "--to",
    type=click.Choice(["coraxml", "trans", "gatejson", "tei", "md"]),
    default="coraxml",
    show_default=True,
    help="Format of the output.",
)
@click.option(
    "-P",
    "--parser",
    type=click.Choice(
        [
            key
            for key in coraxml_utils.parser.dialect_mapper.keys()
            if isinstance(key, str)
        ]
    ),
    default="plain",
    show_default=True,
    help="Token parser to use.",
)
@click.option(
    "--strict/--chill",
    "strict_parsing",
    default=True,
    show_default=True,
    help="Use strict parsing to prevent tokenization changes",
)
@click.option("-o", "--outfile", type=click.File("w"))
def convert(infile, from_, to, parser, strict_parsing, outfile):

    MyImporter = create_importer(from_, parser, strict=strict_parsing)
    MyExporter = create_exporter(to)

    doc = MyImporter.import_from_file(infile)
    if doc:
        outdoc = MyExporter.export(doc)

        # convert special documents to text
        if isinstance(outdoc, dict):
            # json
            outdoc = json.dumps(outdoc)
        elif isinstance(outdoc, etree._ElementTree):
            # xml
            outdoc = etree.tostring(
                outdoc, xml_declaration=True, pretty_print=True, encoding="utf-8"
            )

        # default: text
        click.echo(outdoc, file=outfile)
    else:
        logging.error("Input document invalid")
        exit(1)
