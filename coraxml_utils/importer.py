
import re
import sys
import logging
logging.basicConfig(format='%(levelname)s: %(message)s')
logger = logging.getLogger()

from collections import defaultdict

from coraxml_utils.coralib import *
from coraxml_utils.character import Joiner
import coraxml_utils.parser as parser
import coraxml_utils.tokenizer as tokenizer

from lxml import etree as ET


def create_importer(file_format, dialect=None, **kwargs):
    if file_format == 'coraxml':
        if dialect in parser.dialect_mapper:
            cora_importer = CoraXMLImporter(parser.dialect_mapper[dialect])
            if dialect == 'rem':
                cora_importer.tok_dipl_tag = 'tok_dipl'
                cora_importer.tok_anno_tag = 'tok_anno'
            return cora_importer
        else:
            raise ValueError("CorA-XML dialect " + dialect + " is not supported.")
    elif file_format == "trans":
        if dialect in parser.dialect_mapper:
            return TransImporter(parser.dialect_mapper[dialect], kwargs)
        else:
            raise ValueError("CorA-XML dialect " + dialect + " is not supported.")
    else:
        raise ValueError("File format " + file_format + " is not supported.")

## TODO project specific functions!
def parse_header(header_string):

    header = dict()
    for header_line in header_string.splitlines():
        header_line = header_line.strip()
        ## skip empty lines
        if not header_line:
            continue
        key, *val = header_line.split(':')
        header[key] = val if val else ""

    return header

class CoraXMLImporter:

    def __init__(self, token_parser):
        self.tok_dipl_tag = 'dipl'
        self.tok_anno_tag = 'mod'
        self.tokenparser = token_parser()


    def _create_dipl_token(self, dipl_element):
        return TokDipl(self.tokenparser.parse(dipl_element.attrib['trans'], output_type="dipl"), 
                       extid=dipl_element.attrib['id'])

    def _create_anno_token(self, anno_element):

        # retrieve annotations
        tags = dict()
        flags = set()

        for annotation_element in anno_element:

            if annotation_element.tag == 'cora-flag':
                flagname = annotation_element.attrib['name']
                if flagname in flags:
                    logging.warning('Flag ' + flagname + 
                                    ' is set twice for anno-token ' + anno_element.attrib['id'] + '.')
                flags.add(flagname)
            else:
                tagname = annotation_element.tag
                if tagname in tags:
                    logging.warning('Tag ' + tagname + 
                                    ' is set twice for anno-token ' + anno_element.attrib['id'] + '.')
                tags[tagname] = annotation_element.attrib['tag']

        ## the attribute checked is not obligatory
        checked = 'checked' in anno_element.attrib and anno_element.attrib['checked'] == 'y'

        return TokAnno(
            self.tokenparser.parse(anno_element.attrib['trans'], output_type="anno"),
            tags=tags, flags=flags, checked=checked, extid=anno_element.attrib['id']
        )

    def _create_cora_token(self, coratoken_element):

        dipl_tokens = []
        anno_tokens = []

        for dipl_element in coratoken_element.findall(self.tok_dipl_tag):
            dipl_tokens.append(self._create_dipl_token(dipl_element))
        for anno_element in coratoken_element.findall(self.tok_anno_tag):
            anno_tokens.append(self._create_anno_token(anno_element))

        parsed_token = self.tokenparser.parse(coratoken_element.attrib['trans'])

        ## test if parses match
        parsed_dipl_toks = parsed_token.tokenize_dipl()
        if len(parsed_dipl_toks) != len(dipl_tokens):
            logging.error("Parse does not match number of dipl tokens for token " + coratoken_element.attrib['id'])
        else:
            if any([dipl1.trans() != dipl2.trans.trans() for dipl1, dipl2 in zip(parsed_dipl_toks, dipl_tokens)]):
                logging.error("Transcriptions of dipls are not equal for token " + coratoken_element.attrib['id'])
        parsed_anno_toks = parsed_token.tokenize_anno()
        if len(parsed_anno_toks) != len(anno_tokens):
            logging.error("Parse does not match number of anno tokens for token " + coratoken_element.attrib['id'])
        else:
            if any([anno1.trans() != anno2.trans.trans() for anno1, anno2 in zip(parsed_anno_toks, anno_tokens)]):
                logging.error("Transcriptions of dipls are not equal for token " + coratoken_element.attrib['id'])

        return CoraToken(parsed_token, dipl_tokens, anno_tokens, extid=coratoken_element.attrib['id'])

    def _get_range(self, element):
        return element.attrib['range'].split('..')

    def _connect_with_layout_elements(self, root, layout_type, subelements, subelement_type, 
                                      extract_from_xml, create_object):
        """
        Connects elements like lines with higher element like columns.

        Positional arguments:
        root -- the xml object
        layout_type -- type of the layout element (line, column or page)
        subelement -- list of the elements that should be connected
        subelement_type -- the name of the subelement (used for warnings)
        extract_from_xml -- a function that gets the xml element and returns a dictionary with 
                            all relevant information for the layout element
        create_object -- a function that gets the dictionary from extract_from_xml with added 
                         "subelements" and returns an object representing the layout element
        """
        layout_elements = []

        # get layoutinfo from xml
        beginnings = dict()
        for element in root.findall("layoutinfo/" + layout_type):
            range = self._get_range(element)
            if range[0] in beginnings:
                logging.error('Two ' + layout_type + 's that start at the same position: ' + 
                              element.attrib['id'] + ' and ' + beginnings[range[0]]['extid'])
            beginnings[range[0]] = {**extract_from_xml(element), 
                                    'end': range[-1], 'subelements': []}

        open_element = None
        for subelement in subelements:
            if open_element is None:
                if subelement.id in beginnings:
                    open_element = beginnings.pop(subelement.id)
                else:
                    # warn and continue
                    logging.warn(subelement_type + ' that is not connected to anything in the layout: ' + 
                                 subelement.id)
                    continue

            open_element['subelements'].append(subelement)
            if open_element['end'] == subelement.id:
                layout_elements.append(create_object(open_element))
                open_element = None

        if beginnings:
            logger.warn('Dropped ' + layout_type + 
                        '(s) starting with nonexistent ' + subelement_type + 
                        ': ' + str(list(beginnings.keys())))
        if open_element:
            logger.warn('Dropped ' + layout_type + 
                        '(s) ending with nonexistent ' + subelement_type + 
                        ': ' + open_element['extid'])

        return layout_elements


    def import_from_file(self, filename):

        tree = ET.parse(filename, ET.XMLParser())
        root = tree.getroot()

        ## Create list of cora_tokens and comments and a list of dipl_tokens for the layout elements
        tokens = []
        dipl_tokens = []
        for element in root:

            if element.tag == 'token':
                curr_token = self._create_cora_token(element)
                tokens.append(curr_token)
                dipl_tokens.extend(curr_token.tok_dipls)
            elif element.tag == 'comment':
                tokens.append(CoraComment(element.attrib['type'], element.text))

        # Get shifttags
        shifttag_beginnings = defaultdict(list)
        shifttags = []
        open_shifttags = []

        for shifttag_element in root.find('shifttags'):
            range = self._get_range(shifttag_element)
            shifttag_beginnings[range[0]].append({
                'type': shifttag_element.tag,
                'end': range[-1],
                'tokens': []
            })

        for cora_token in tokens:
            # Skip comments
            if isinstance(cora_token, CoraComment):
                continue
            # move shifttags that start with the current token to open_shifttags
            if cora_token.id in shifttag_beginnings:
                open_shifttags.extend(shifttag_beginnings.pop(cora_token.id))
            # add token to all open_shifttags and create shifttag objects for finished shifttags
            still_open_shifttags = []
            for shifttag in open_shifttags:
                shifttag['tokens'].append(cora_token)
                if cora_token.id == shifttag['end']:
                    shifttags.append(ShiftTag(shifttag['type'], shifttag['tokens']))
                else:
                    still_open_shifttags.append(shifttag)
            open_shifttags = still_open_shifttags

        if shifttag_beginnings:
            logging.warn("Dropped shifttag(s) starting with nonexistent token: " + str(list(shifttag_beginnings.keys())))

        if open_shifttags:
            logging.warn("Dropped shifttag(s) ending with nonexistent token: " + str([shifttag['end'] for shifttag in open_shifttags]))

        # Get layout info
        lines = self._connect_with_layout_elements(root, 'line', dipl_tokens, 'dipl token',
                              lambda element: {'extid': element.attrib['id'], 'name': element.attrib['name']},
                              lambda dictionary: Line(dictionary['name'], dictionary['subelements'], extid=dictionary['extid']))
        columns = self._connect_with_layout_elements(root, 'column', lines, 'line',
                              lambda element: {'extid': element.attrib['id']},
                              lambda dictionary: Column(dictionary['subelements'], extid=dictionary['extid']))
        pages = self._connect_with_layout_elements(root, 'page', columns, 'column',
                              lambda element: {'extid': element.attrib['id'], 'name': element.attrib['no'], 'side': element.attrib.get('side', None)},
                              lambda dictionary: Page(dictionary['name'], dictionary['side'], dictionary['subelements'], extid=dictionary['extid']))
        ## collect document information and create Document object
        sigle = ""
        name = ""
        cora_header = root.find('cora-header')
        if cora_header is not None:
            sigle = cora_header.get("sigle", "")
            name = cora_header.get("name", "")

        # get header
        header_element = root.find("header")
        header_string = ET.tostring(header_element, encoding="unicode", method="xml")
        if not list(header_element):
            header = parse_header(ET.tostring(header_element, encoding="unicode", method="text"))
        else:
            # header is structured as xml - transform to dict
            header = dict()
            for header_part in header_element:
                header[header_part.tag] = header_part.text

        return Document(sigle, name, header, pages, tokens, shifttags, header_string)


class TransImporter:

    def __init__(self, parser, options):
        self.TokenParser = parser()
        self.Tokenizer = tokenizer.RexTokenizer()
        # allowed bibinfo format
         # pageno, side, col, linename
        self.BIBINFO_FORMAT = re.compile(r"""^(?P<sigle>\S+)[-_]
                                             (?P<page>[A-Z0-9]*)
                                             (?P<side>[vr]?)
                                             (?P<col>[a-q]?),?
                                             (?P<line>\d+)$""", re.VERBOSE)

    # TODO: transcription importer should also check bibinfo, shifttags, etc. and
    #   warn or report errors as appropriate (would replace parts of "convert_check"
    #   script) -- aka. *checking is default behavior*, new script does conversion
    def import_from_string(self, intext):

        new_doc = Document("", "", None, list(), list())
        self.valid_transcription = True

        # read header
        header_open = False
        header_lines = list()
        text = list()

        for line in intext.splitlines():
            if line.strip() == "+H":
                header_open = True
            elif line.strip() == "@H":
                header_open = False
            elif header_open:
                header_lines.append(line)
            elif line and not header_open:
                text.append(line)
            else:
                # skip empty lines
                pass

        if not header_lines:
            logging.error("Header is empty!")

        new_doc.header_string = "\n".join(header_lines)
        new_doc.header = parse_header(new_doc.header_string)
        try:
            new_doc.sigle = re.search(r"[^:\s]:\s+([\w\d]+)", 
                                      new_doc.header_string).group(1)
        except AttributeError:
            logging.warning("No sigle found in document header!")

        open_shifttags = list()
        shifttag_stack = list()

        bibinfo_lines = list()
        transcription_content = list()
        for line in text:
            try:
                bibinfo, content = re.split(r"\t+", line.strip(), maxsplit=1)
                # if _: logging.warning("extraneous tab in line: " + line)
                transcription_content.append(content)
                bibinfo_lines.append(bibinfo)
            except ValueError:
                logging.warning("Faulty line: " + repr(line))
        tokenized_input = self.Tokenizer.tokenize("\n".join(transcription_content))

        bibinfo_iter = iter(bibinfo_lines)
        new_bibinfo = self.BIBINFO_FORMAT.match(next(bibinfo_iter)).groupdict()
        current_line = new_doc.add_line(new_bibinfo)

        for chunk in tokenized_input:
            if isinstance(chunk, tokenizer.Comment):
                new_doc.tokens.append(CoraComment(chunk.type, chunk.content))
            elif isinstance(chunk, tokenizer.ShiftTagOpen):
                open_shifttags.append(chunk.type)
            elif isinstance(chunk, tokenizer.ShiftTagClose):
                closed_shifttag = open_shifttags.pop()
                new_doc.shifttags.append(ShiftTag(closed_shifttag, shifttag_stack))
                if not open_shifttags:
                    shifttag_stack = list()

            elif isinstance(chunk, tokenizer.Token):
                try:
                    new_token = self.TokenParser.parse(chunk.string)
                except parser.ParseError as e:
                    logging.error("Transcription could not be parsed: {0}\t{1}".format(new_bibinfo,
                                                                                       chunk.string))
                    print(e.message)
                    self.valid_transcription = False

                    #  in case the erroneous transcription also contains a newline
                    for c in chunk.string:
                        if c == "\n":
                             # start a new line
                            try:
                                new_bibinfo = self.BIBINFO_FORMAT.match(next(bibinfo_iter)).groupdict()
                                current_line = new_doc.add_line(new_bibinfo)
                            except StopIteration:
                                print(new_bibinfo)
                                logging.error("Document appears truncated: " + str(new_token))                           

                    continue

                t = CoraToken(new_token, [], [])
                mydipls = [TokDipl(dipl) for dipl in new_token.tokenize_dipl()]
                t.tok_dipls = list(mydipls)

                mydipls.reverse()
                for c in new_token.parse:
                    if c.dipl_bound:
                        current_line.dipls.append(mydipls.pop())

                    if c.string == "\n":
                        # start a new line
                        try:
                            new_bibinfo = self.BIBINFO_FORMAT.match(next(bibinfo_iter)).groupdict()
                            current_line = new_doc.add_line(new_bibinfo)
                        except StopIteration:
                            print(new_bibinfo)
                            logging.error("Document appears truncated: " + str(new_token))

                current_line.dipls.append(mydipls.pop())
                # make sure that mydipls is empty
                if mydipls:
                    logging.error("Too few dipl bounds: " + str(new_token))

                for anno in new_token.tokenize_anno():
                    t.tok_annos.append(TokAnno(anno))

                new_doc.tokens.append(t)
                # if open_shifttags, add new coratoken obj 
                if open_shifttags:
                    shifttag_stack.append(t)


                            
            elif isinstance(chunk, tokenizer.Whitespace):
                if chunk.is_newline:
                    # open new line
                    try:
                        new_bibinfo = self.BIBINFO_FORMAT.match(next(bibinfo_iter)).groupdict()
                        current_line = new_doc.add_line(new_bibinfo)
                    except StopIteration:
                        pass

        try:
            leftover_bibinfo = next(bibinfo_iter)
            if leftover_bibinfo:
                logging.warning("Bibinfo iterator not empty: line numbers probably wrong")
                print(leftover_bibinfo)
                print(list(bibinfo_iter))
        except StopIteration:
            pass
        if self.valid_transcription:
            return new_doc
        else:
            return None
