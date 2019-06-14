import json
import click

from lxml import etree as ET

import coraxml_utils.parser
from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter

@click.group()
def main():
    pass

@main.command()
@click.argument('infile', type=click.File('r'))
@click.option('-f', '--from', 'from_',
              type=click.Choice(['coraxml', 'bonnxml', 'trans']),
              default='trans', show_default=True, help="Format of the input."
)
@click.option('-t', '--to',
              type=click.Choice(['coraxml', 'trans', 'gatejson', 'tei', 'md']),
              default='coraxml', show_default=True, help="Format of the output."
)
@click.option('-P', '--parser',
              type=click.Choice([
                  key for key in coraxml_utils.parser.dialect_mapper.keys()
                  if isinstance(key, str)
              ]),
              default='plain', show_default=True,
              help="Token parser to use.")
@click.option('-o', '--outfile', type=click.File('w'))
def convert(infile, from_, to, parser, outfile):

    MyImporter = create_importer(from_, parser)
    MyExporter = create_exporter(to)

    doc = MyImporter.import_from_file(infile)
    outdoc = MyExporter.export(doc)

    ## convert special documents to text
    if isinstance(outdoc, dict):
        ## json
        outdoc = json.dumps(outdoc)
    elif isinstance(outdoc, ET._ElementTree):
        ## TODO is this a nice way to test for elementtree?
        ## xml
        outdoc = ET.tostring(outdoc, xml_declaration=True,
                             pretty_print=True, encoding='utf-8')

    ## default: text
    click.echo(outdoc, file=outfile)
