
import re
import itertools
import sys
import logging
logging.basicConfig(format='%(levelname)s: %(message)s')
logger = logging.getLogger()

from collections import defaultdict

from coraxml_utils.coralib import *
from coraxml_utils.character import LineBreak, Joiner
import coraxml_utils.parser as parser
import coraxml_utils.tokenizer as tokenizer

from lxml import etree as ET


def create_importer(file_format, dialect=None, **kwargs):
    if file_format == 'coraxml':
        if dialect in parser.dialect_mapper:
            cora_importer = CoraXMLImporter(parser.dialect_mapper[dialect], **kwargs)
            if dialect == 'rem':
                cora_importer.tok_dipl_tag = 'tok_dipl'
                cora_importer.tok_anno_tag = 'tok_anno'
            return cora_importer
        else:
            raise ValueError("CorA-XML dialect " + dialect + " is not supported.")
    elif file_format == "bonnxml":
        if dialect in parser.dialect_mapper:
            return BonnXMLImporter(parser.dialect_mapper[dialect], **kwargs)
        else:
            raise ValueError("CorA-XML dialect " + dialect + " is not supported.")
    elif file_format == "trans":
        if dialect in parser.dialect_mapper:
            return TransImporter(parser.dialect_mapper[dialect], **kwargs)
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

    def __init__(self, token_parser, strict=True):
        self.tok_dipl_tag = 'dipl'
        self.tok_anno_tag = 'mod'
        self.tokenparser = token_parser()

        self.strict = strict


    def _create_dipl_token(self, dipl_element, trans):

        return TokDipl(trans, extid=dipl_element.attrib['id'])

    def _create_anno_token(self, anno_element, trans):

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
                tags[tagname] = annotation_element.attrib.get('tag', "")

        ## the attribute checked is not obligatory
        checked = 'checked' in anno_element.attrib and anno_element.attrib['checked'] == 'y'

        return TokAnno(trans,
            tags=tags, flags=flags, checked=checked, extid=anno_element.attrib['id']
        )

    def _create_cora_token(self, coratoken_element, line_endings):

        ## get dipl and anno elements
        dipl_tokens = []
        anno_tokens = []

        for dipl_element in coratoken_element.findall(self.tok_dipl_tag):
            dipl_tokens.append(dipl_element)
        for anno_element in coratoken_element.findall(self.tok_anno_tag):
            anno_tokens.append(anno_element)

        ## test that transcriptions are the same for the different levels
        token_trans = coratoken_element.attrib['trans']
        dipl_trans = "".join([dipl_element.attrib['trans'] for dipl_element in dipl_tokens])
        anno_trans = "".join([anno_element.attrib['trans'] for anno_element in anno_tokens])

        if dipl_trans != token_trans:
            logging.warning("Transcription of virtual token does not equal the concatenation of the dipl-token transcriptions. Dipl transcriptions is used for token " +
                            coratoken_element.attrib['id'] + " (" + coratoken_element.attrib['trans'] + ").")
        if anno_tokens and anno_trans != dipl_trans:
            logging.warning("Concatenation of anno-token transcriptions does not equal the concatenation of the dipl-token transcriptions. Dipl transcription is used for token " +
                            coratoken_element.attrib['id']  + " (" + coratoken_element.attrib['trans'] + ").")


        ## create transcription of the token with linebreaks
        parse_trans = ''
        for dipl_tok in dipl_tokens:
            parse_trans += dipl_tok.attrib['trans']
            if dipl_tok.attrib['id'] in line_endings:
                parse_trans += '\n'
        parse_trans = parse_trans.strip()

        trans_valid = True

        try:
            parsed_token = self.tokenparser.parse(parse_trans)
            ## test if parses match
            parsed_dipl_toks = parsed_token.tokenize_dipl()
            if len(parsed_dipl_toks) != len(dipl_tokens):
                logging.warning("Parse does not match number of dipl tokens for token " + coratoken_element.attrib['id'])
                trans_valid = False
            else:
                if any([dipl1.trans() != dipl2.attrib['trans'] for dipl1, dipl2 in zip(parsed_dipl_toks, dipl_tokens)]):
                    logging.warning("Transcriptions of dipls are not equal for token " + coratoken_element.attrib['id'])
            parsed_anno_toks = parsed_token.tokenize_anno()
            if len(parsed_anno_toks) != len(anno_tokens):
                logging.warning("Parse does not match number of anno tokens for token " + coratoken_element.attrib['id'] +
                              " " + coratoken_element.attrib['trans'])
                trans_valid = False
            else:
                if any([anno1.trans() != anno2.attrib['trans'] for anno1, anno2 in zip(parsed_anno_toks, anno_tokens)]):
                    logging.warning("Transcriptions of annos are not equal for token " + coratoken_element.attrib['id'])

            ### Transform XML-Elements into objects
            if trans_valid:

                dipl_tokens = [self._create_dipl_token(dipl_element, dipl_parse)
                               for dipl_element, dipl_parse in zip(dipl_tokens, parsed_dipl_toks)]

                anno_tokens = [self._create_anno_token(anno_element, anno_parse)
                               for anno_element, anno_parse in zip(anno_tokens, parsed_anno_toks)]

            else:

                dipl_tokens = [self._create_dipl_token(dipl_element, self.tokenparser.parse(dipl_element.attrib['trans'], output_type="dipl"))
                               for dipl_element in dipl_tokens]

                anno_tokens = [self._create_anno_token(anno_element, self.tokenparser.parse(anno_element.attrib['trans'], output_type="anno"))
                               for anno_element in anno_tokens]

                if self.strict:
                    self.valid_document = False
                    logging.error("Tokenization given in XML does not match tokenization of the given parser for token " + coratoken_element.attrib['id']  + " (" + coratoken_element.attrib['trans'] + ").")
                else:
                    logging.warning("Tokenization given in XML does not match tokenization of the given parser - using tokenization from XML. This might lead to unexpected behaviour!")


            return CoraToken(parsed_token, dipl_tokens, anno_tokens, extid=coratoken_element.attrib['id'])

        except parser.ParseError as e:
            ## parse error - return an empty token
            logging.error("Token could not be parsed: " + parse_trans + " Message: " + e.message)
            trans_valid = False
            return CoraToken(None, [], [], extid=coratoken_element.attrib['id'])


    def _get_range(self, element):
        if element.attrib['range']:
            return element.attrib['range'].split('..')
        else:
            ## empty range - should not happen but appears sometimes
            return None

    def _connect_with_layout_elements(self, root, layout_type, subelements, subelement_type, 
                                      extract_from_xml, create_object):
        """
        Connects elements like lines with higher elements like columns.

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
        beginnings = []
        for element in root.findall("layoutinfo/" + layout_type):
            range = self._get_range(element)
            if range is None:
                logging.warn('Dropped empty ' + layout_type + ' (' + element.attrib['id'] + ')')
                continue
            if range[0] in beginnings:
                logging.error('Two ' + layout_type + 's that start at the same position: ' + 
                              element.attrib['id'] + ' and ' + beginnings[range[0]]['extid'])
            beginnings.append({**extract_from_xml(element), 
                               'beginning': range[0], 
                               'end': range[-1], 'subelements': []})

        beginnings.reverse()
        next_element = beginnings.pop()
        open_element = False

        for subelement in subelements:

            if next_element is None:
                logging.warn('No more ' + layout_type + 's for ' + subelement_type + ' (' + subelement.id +  ')')

            if not open_element:
                if subelement.id == next_element['beginning']:
                    open_element = True
                else:
                    # warn and continue
                    logging.warn('Expected ' + subelement_type + ' with id ' + next_element['beginning'] +
                                 ' but found ' + subelement_type + ' with id ' + subelement.id)

            next_element['subelements'].append(subelement)
            if next_element['end'] == subelement.id:
                layout_elements.append(create_object(next_element))
                open_element = False
                if beginnings:
                    next_element = beginnings.pop()
                else:
                    next_element = None

        if beginnings:
            logger.warn('Dropped ' + layout_type + 
                        '(s) starting with nonexistent ' + subelement_type + 
                        ': ' + str([beginning['extid'] for beginning in reversed(beginnings)]))
        if open_element:
            logger.warn('Dropped ' + layout_type + 
                        '(s) ending with nonexistent ' + subelement_type + 
                        ': ' + next_element['extid'])

        return layout_elements


    def import_from_file(self, filename):

        self.valid_document = True

        tree = ET.parse(filename, ET.XMLParser())
        root = tree.getroot()

        ## get all ids of last dipls in line
        line_endings = set()
        for element in root.findall("layoutinfo/line"):
            range = self._get_range(element)
            if range is not None:
                line_endings.add(range[-1])

        ## Create list of cora_tokens and comments and a list of dipl_tokens for the layout elements
        tokens = []
        dipl_tokens = []
        for element in root:

            if element.tag == 'token':
                curr_token = self._create_cora_token(element, line_endings)
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

        if self.valid_document:
            return Document(sigle, name, header, pages, tokens, shifttags, header_string)
        else:
            return None


class TransImporter:

    def __init__(self, parser):
        self.TokenParser = parser()
        self.Tokenizer = tokenizer.RexTokenizer()
        # allowed bibinfo format
         # pageno, side, col, linename
        self.BIBINFO_FORMAT = re.compile(r"""^(?P<sigle>\S+)[-_]
                                             (?P<page>[A-Z0-9]*)
                                             (?P<side>[vr]?)
                                             (?P<col>[a-q]?),?
                                             (?P<line>\d+)$""", re.VERBOSE)

    def _add_line(self, document, bibinfo, dipl_tokens):

        if not dipl_tokens:
            logging.warning("Line contains no token - skipped: {sigle}-{page}{side}{col},{line}".format(**bibinfo))
        else:
            line = document.add_line(bibinfo)
            line.dipls = dipl_tokens

    def _parse_bibinfos(self, bibinfo_strings):

        bibinfos = []
        for line, bibinfo in enumerate(bibinfo_strings):
            if bibinfo is not None:
                try:
                    bibinfos.append(self.BIBINFO_FORMAT.match(bibinfo).groupdict())
                except:
                    logging.error("Bibinfo hat falsches Format (Zeile {}): {}".format(line+1, bibinfo))
                    self.valid_transcription = False
                    ## use last bibinfo to create current info
                    curr_bibinfo = dict(bibinfos[-1])
                    curr_bibinfo['line'] = '%02d' % (int(curr_bibinfo['line']) + 1)
                    bibinfos.append(curr_bibinfo)
            else:
                curr_bibinfo = dict(bibinfos[-1])
                curr_bibinfo['line'] = '%02d' % (int(curr_bibinfo['line']) + 1)
                bibinfos.append(curr_bibinfo)

        return bibinfos

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
            if "_" in new_doc.sigle:
                new_doc.sigle = new_doc.sigle.split("_")[0]
        except AttributeError:
            logging.warning("No sigle found in document header!")

        open_shifttags = list()
        shifttag_stack = list()

        bibinfo_lines = list()
        transcription_content = list()
        for line in text:
            if "\t" in line.strip():
                try:
                    bibinfo, content = re.split(r"\t+", line.strip(), maxsplit=1)
                    # if _: logging.warning("extraneous tab in line: " + line)
                    transcription_content.append(content)
                    bibinfo_lines.append(bibinfo)
                except ValueError:
                    logging.warning("Faulty line: " + repr(line))
            else:
                transcription_content.append(line.strip())
                bibinfo_lines.append(None)
        tokenized_input = self.Tokenizer.tokenize("\n".join(transcription_content))

        bibinfo_lines = self._parse_bibinfos(bibinfo_lines)

        bibinfo_iter = iter(bibinfo_lines)
        current_line_dipls = []

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
                    new_token = self.tokenparser.parse(chunk.string)
                except parser.ParseError as e:
                    ## get next line
                    new_bibinfo = next(bibinfo_iter)
                    bibstr = "{sigle}-{page}{side}{col},{line}".format(**new_bibinfo)
                    ## put line back to iterator
                    bibinfo_iter = itertools.chain([new_bibinfo], bibinfo_iter)
                    logging.error("Transcription could not be parsed: {0}\t{1}".format(bibstr,
                                                                                       chunk.string))
                    print(e.message)
                    self.valid_transcription = False

                    #  in case the erroneous transcription also contains a newline
                    for c in chunk.string:
                        if c == "\n":
                             # start a new line
                            try:
                                current_line_dipls[-1].trans.parse[-1].line_break_after = True
                                self._add_line(new_doc, next(bibinfo_iter), current_line_dipls)
                                current_line_dipls = []
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
                        current_line_dipls.append(mydipls.pop())

                    if isinstance(c, LineBreak):
                        # start a new line
                        try:
                            current_line_dipls[-1].trans.parse[-1].line_break_after = True
                            self._add_line(new_doc, next(bibinfo_iter), current_line_dipls)
                            current_line_dipls = []
                        except StopIteration:
                            print(new_bibinfo)
                            logging.error("Document appears truncated: " + str(new_token))
                        except AttributeError as e:
                            if not bibinfo_match:
                                logging.error("Bibinfo '{0}' has wrong format".format(next_bibinfo))
                            else:
                                raise e

                current_line_dipls.append(mydipls.pop())
                # make sure that mydipls is empty
                if mydipls:
                    logging.error("Too few dipl bounds: " + str(new_token))

                for anno in new_token.tokenize_anno():
                    t.tok_annos.append(TokAnno(anno))

                new_doc.tokens.append(t)
                # if open_shifttags, add new coratoken obj 
                if open_shifttags:
                    shifttag_stack.append(t)


                            
            elif isinstance(chunk, tokenizer.Newline):
                ## add line to document
                try:
                    current_line_dipls[-1].trans.parse[-1].line_break_after = True
                    self._add_line(new_doc, next(bibinfo_iter), current_line_dipls)
                    current_line_dipls = []
                except StopIteration:
                    pass
                except AttributeError as e:
                    if not bibinfo_match:
                        logging.error("Bibinfo '{0}' has wrong format".format(next_bibinfo))
                    else:
                        raise e
                    

        ## add last line
        if current_line_dipls:
            current_line_dipls[-1].trans.parse[-1].line_break_after = True
            self._add_line(new_doc, next(bibinfo_iter), current_line_dipls)

        try:
            leftover_bibinfo = next(bibinfo_iter)
            if leftover_bibinfo:
                logging.warning("Bibinfo iterator not empty: line numbers probably wrong")
                print(leftover_bibinfo)
                print(list(bibinfo_iter))
        except StopIteration:
            pass

        if self.valid_transcription:
            ## create indices of lines and dipl tokens
            new_doc._create_indices()
            return new_doc
        else:
            return None

class BonnXMLImporter:
    
    def __init__(self, token_parser):
        self.tokenizer = tokenizer.RexTokenizer()
        self.tokenparser = token_parser()

    def _create_header(self, bonnHeader, output="dict"):
        
        #Header mapping
        #(BonnXML element name, attribute name, target name)
        header_mapping = [("general/title", "val", "text"), \
                          ("general/abbreviation", "ab_ddd", "abbr_ddd"), \
                          ("general/abbreviation", "ab_mwb", "abbr_mwb"), \
                          ("general/text_field", "val", "topic"), \
                          ("general/text_type", "val", "text-type"), \
                          ("general/text_form", "val", "genre"), \
                          ("general/ref", "val", "reference"), \
                          ("general/sec_ref", "val", "reference-secondary"), \
                          ("document_medium/library", "val", "library"), \
                          ("document_medium/shelfmark", "val", "library-shelfmark"), \
                          ("document_medium/census", "val", "online"), \
                          ("entry/medium_type", "val", "medium"), \
                          ("entry/extent", "val", "extent"), \
                          ("entry/extract", "val", "extract"), \
                          ("entry/language", "val", "language"), \
                          ("entry/dialect_region", "val", "language-type"), \
                          ("entry/dialect_area", "val", "language-region"), \
                          ("entry/dialect", "val", "language-area"), \
                          ("entry/localization", "val", "place"), \
                          ("entry/dating", "val", "time"), \
                          ("entry/specific_features", "val", "notes-manuscript"), \
                          ("text/text_dating", "val", "date"), \
                          ("text/text_localization", "val", "text-place"), \
                          ("text/author", "val", "text-author"), \
                          ("text/textdialect", "val", "text-language"), \
                          ("text/foreign_language_dependence", "val", "text-source"), \
                          ("text/edition", "val", "edition"), \
                          ("corpusStmt/corpus", "val", "corpus"), \
                          ("corpusStmt/transcription_notes", "val", "notes-transcription"), \
                          ("corpusStmt/annotation_notes", "val", "notes-annotation"), \
                          ("respStmt/digitization", "val", "digitization_by"), \
                          ("respStmt/collation", "val", "collation_by"), \
                          ("respStmt/pre_editing", "val", "pre_editing_by"), \
                          ("respStmt/annotation", "val", "annotation_by"), \
                          ("respStmt/proofreading", "val", "proofreading_by")]

        #If output should be a dictionary:
        if output == "dict":
            
            #Create new header.
            header = dict()

            #For each mapping:
            for mapping in header_mapping:

                #If the element exists in the BonnXML header:
                elem = bonnHeader.find(mapping[0])
                if elem is not None:

                    #Add the information from BonnXML with the target name.
                    header[mapping[2]] = elem.attrib[mapping[1]]

                else:
                    #Otherwise add an empty string.
                    header[mapping[2]] = ""
              
        #Otherwise create an XML subtree.
        else:
            
            #Create new header element.
            header = ET.Element("header")

            #For each mapping:
            for mapping in header_mapping:

                #If the element exists in the bonnXML header:
                elem = bonnHeader.find(mapping[0])
                if elem is not None:

                    #Create a new header subelement
                    #containing the information from bonnXML.
                    child = ET.SubElement(header, mapping[2])
                    child.text = elem.attrib[mapping[1]]

                else:
                    #Otherwise set the text value to "".
                    child = ET.SubElement(header, mapping[2])
                    child.text = ""

            #If the output should be a string
            #convert the XML tree to a string.
            if output == "string":
                header = ET.tostring(header, encoding="utf-8", method="xml")

        if not header:
            logging.error("Header is empty!")
            
        #Return the header dictionary, string or element.
        return header

    def _create_dipl_token(self, trans):
        return TokDipl(trans)

    def _create_anno_token(self, trans):
        return TokAnno(trans)

    def _get_annotation(self, anno, bonn_token):
        norm = bonn_token.find("form")
        if norm is not None and "normu" in norm.attrib:
            norm = norm.attrib["normu"]
        if not norm: norm = "--"
        anno.tags["norm"] = norm

        lemma = bonn_token.find("lemma")
        if lemma is not None and "inst" in lemma.attrib:
            lemma = lemma.attrib["inst"]
        if not lemma: lemma = "--"
        anno.tags["lemma"] = lemma
        
        lemma_gen = bonn_token.find("lemma")
        if lemma_gen is not None and "gen" in lemma_gen.attrib:
            lemma_gen = lemma_gen.attrib["gen"]
        if not lemma_gen: lemma_gen = "--"
        anno.tags["lemma_gen"] = lemma_gen
        
        lemma_idmwb = bonn_token.find("lemma")
        if lemma_idmwb is not None and "idmwb" in lemma_idmwb.attrib:
            lemma_idmwb = lemma_idmwb.attrib["idmwb"]
        if not lemma_idmwb: lemma_idmwb = "--"
        anno.tags["lemma_idmwb"] = lemma_idmwb

        pos = bonn_token.find("pos")
        if pos is not None and "inst" in pos.attrib:
            pos = pos.attrib["inst"]
        if pos: anno.tags["pos"] = pos
        
        pos_gen = bonn_token.find("pos")
        if pos_gen is not None and "gen" in pos_gen.attrib:
            pos_gen = pos_gen.attrib["gen"]
        if pos_gen: anno.tags["pos_gen"] = pos_gen
        
        infl = bonn_token.find("infl")
        if infl is not None and "val" in infl.attrib:
            infl = infl.attrib["val"].replace("_", ".")
        if not infl: infl = "--"
        anno.tags["infl"] = infl
        
        inflClass = bonn_token.find("inflClass")
        if inflClass is not None and "inst" in inflClass.attrib:
            inflClass = inflClass.attrib["inst"].replace("_", ".")
        if not inflClass: inflClass = "--"
        anno.tags["inflClass"] = inflClass

        inflClass_gen = bonn_token.find("inflClass")
        if inflClass_gen is not None and "gen" in inflClass_gen.attrib:
            inflClass_gen = inflClass_gen.attrib["gen"].replace("_", ".")
        if not inflClass_gen: inflClass_gen = "--"
        anno.tags["inflClass_gen"] = inflClass_gen

        grapho = bonn_token.find("grapho")
        if grapho is not None and "val" in grapho.attrib:
            grapho = grapho.attrib["val"]
        if not grapho: grapho = "--"
        anno.tags["grapho"] = grapho

        comment = bonn_token.find("comment")
        if comment is not None and "val" in comment.attrib:
            comment = comment.attrib["val"]
            anno.tags["comment"] = comment

        ref_second = bonn_token.find("ref_second")
        if ref_second is not None:
            if "folio2" in ref_second.attrib:
                folio = ref_second.attrib["folio2"]
                anno.tags["ref_second_folio"] = folio
            if "side2" in ref_second.attrib:
                side = ref_second.attrib["side2"]
                anno.tags["ref_second_side"] = side
            if "line2" in ref_second.attrib:
                line = ref_second.attrib["line2"]
                anno.tags["ref_second_line"] = line
            if "token2" in ref_second.attrib:
                token = ref_second.attrib["token2"]
                anno.tags["ref_second_token"] = token                

        return anno

    def _get_structure_of_bonn_xml(self, root):
        #Get document structure
        #[[(pagename, sidename), [[columnname, [[linename, [tok1, tok2, ...]],
        #                                       [linename, [...]],
        #                                        ...
        #                                      ]
        #                         ],
        #                         [columnname, [...]],
        #                         ...
        #                        ],
        # ],
        # [(pagename, sidename), [...]
        # ],
        # ...
        #]
        structure = []
        
        #For each page element
        for page_elem in root.findall("page"):

            #If there are side elements
            if page_elem.findall("side"):

                #For each side element
                for side_elem in page_elem.findall("side"):

                    #Save [(pagename, sidename), [columnslist]]
                    structure.append([(page_elem.attrib["count"], side_elem.attrib["count"]), []])

                    #If there are column elements
                    if side_elem.findall("column"):

                        #For each column element
                        for column_elem in side_elem.findall("column"):

                            #Save [columnname, [lineslist]]
                            structure[-1][-1].append([column_elem.attrib["count"], []])

                            #For each line in the column
                            for line_index, line_elem in enumerate(column_elem.findall("line")):

                                #Save [linename, [tokenslist]]
                                structure[-1][-1][-1][-1].append([str(line_index+1), []])

                                #For each token in the line
                                for token_elem in line_elem.findall("token"):

                                    #Append the token element to the line list
                                    structure[-1][-1][-1][-1][-1][-1].append(token_elem)

                    #If there are only line elements
                    else:

                        #Append a dummy column
                        structure[-1][-1].append(["", []])

                        #For each line element
                        for line_index, line_elem in enumerate(side_elem.findall("line")):

                            #Save [linename, [tokenslist]]
                            structure[-1][-1][-1][-1].append([str(line_index+1), []])

                            #For each token in the line
                            for token_elem in line_elem.findall("token"):

                                #Append the token element to the line list
                                structure[-1][-1][-1][-1][-1][-1].append(token_elem)
                            
            #If there are no side but column elements
            elif page_elem.findall("column"):

                #Save [(pagename, empty sidename), [columnslist]]
                structure.append([(page_elem.attrib["count"], ""), []])

                #For each column element
                for column_elem in page_elem.findall("column"):

                    #Save [columnname, [lineslist]]
                    structure[-1][-1].append([column_elem.attrib["count"], []])

                    #For each line in the column
                    for line_index, line_elem in enumerate(column_elem.findall("line")):

                        #Save [linename, [tokenslist]]
                        structure[-1][-1][-1][-1].append([str(line_index+1), []])

                        #For each token in the line
                        for token_elem in line_elem.findall("token"):

                            #Append the token element to the line list
                            structure[-1][-1][-1][-1][-1][-1].append(token_elem)
                                                        
            #If there are neither sides nor columns, only lines
            else:

                #Save [(pagename, empty sidename), [columnslist]]
                structure.append([(page_elem.attrib["count"], ""), []])

                #Append a dummy column
                structure[-1][-1].append(["", []])

                #For each line element
                for line_index, line_elem in enumerate(page_elem.findall("line")):

                    #Save [linename, [tokenslist]]
                    structure[-1][-1][-1][-1].append([str(line_index+1), []])

                    #For each token in the line
                    for token_elem in line_elem.findall("token"):
                        
                        #Append the token element to the line list
                        structure[-1][-1][-1][-1][-1][-1].append(token_elem)

        return structure

    def _get_transcription_from_bonn_xml(self, structure):
        #Get full transcription
        #with tokens separated by spaces
        #and lines indicated by \n
        transcription = ""
        for page in structure:
            for column in page[-1]:
                for line in column[-1]:
                    for index,token in enumerate(line[-1]):
                        if index == 0:
                            transcription = transcription + token.find("form").attrib["trans"]
                        else:
                            transcription = transcription + " " + token.find("form").attrib["trans"]
                        if index == len(line[-1])-1:
                            transcription = transcription + "\n"
        transcription = transcription.strip()
        return transcription
    
    def _preprocess_transcription(self, transcription):

        #Remove whitespace surrounding |
        transcription = re.sub(r" *\| *", "|", transcription)

        #Move newlines inside of words
        #e.g. uil=|\n|er -> uil=||er\n
        tokens = transcription.split(" ")
        t = 0
        while t < len(tokens)-1:
            if "|\n" in tokens[t]:
                tokens[t] = tokens[t].replace("|\n", "|", 1)+ "\n"
            t+=1
        transcription = " ".join(tokens)

        #Replace double || with a single |
        transcription = re.sub(r"\|\|", "|", transcription)

        #Correct line boundaries.
        lines = [line.split() for line in transcription.split("\n")]
        for l in range(len(lines)):
            line = lines[l]

            #If the first token of a line contains a =
            if "=" in line[0]:
                pass
                #logging.warn("Found = in first token '{0}' of line {1}.".format(line[0], l+1))

            #If a token in the middle of the line contains a =    
            if any("=" in line[i] for i in range(1, len(line)-1)):
                pass
                #logging.warn("Found = in the middle of line {0}.".format(l+1))

            #If the last token contains a =
            if "=" in line[-1]:

                #If this is not the last line of the document,
                #move the rest of the word to the next line.
                if l < len(lines)-1:
                    
                    #If (=)| or =| or =
                    if re.search(r"=[>\)]*\|*", line[-1]):
                        i_split = re.search(r"=[>\)]*\|*", line[-1]).span()[-1]
                        lines[l+1].insert(0, line[-1][i_split:])
                        lines[l][-1] = line[-1][:i_split]

                    #If |(=) or |=
                    elif re.search(r"\|*[<\(]*=", line[-1]):
                        i_split = re.search(r"\|*[<\(]*=", line[-1]).span()[-1]
                        lines[l+1].insert(0, line[-1][i_split:])
                        lines[l][-1] = line[-1][:i_split]

                #If this is the last line do nothing.
                else:
                    pass
                    #logging.warn("Found = in the last token '{0}' of the text.".format(line[-1]))

        #Rejoin and return the transcription.
        transcription = "\n".join([" ".join(line) for line in lines])
        return transcription

    def _create_cora_tokens(self, tokenized_input):
        open_shifttags = list()
        shifttag_stack = list()
        shifttags = list()
        
        trans_valid = True
        
        cora_tokens = []

        #Parse tokenized transcription.
        for chunk in tokenized_input:
            try:
                if isinstance(chunk, tokenizer.Comment):
                    cora_tokens.append(CoraComment(chunk.type, chunk.content))
                    
                elif isinstance(chunk, tokenizer.Token):
                    parsed_token = self.tokenparser.parse(chunk.string)
                    parsed_dipl_toks = parsed_token.tokenize_dipl()
                    parsed_anno_toks = parsed_token.tokenize_anno()

                    #Transform parses into objects.
                    dipl_tokens = [self._create_dipl_token(dipl_tok) for dipl_tok in parsed_dipl_toks]
                    anno_tokens = [self._create_anno_token(anno_tok) for anno_tok in parsed_anno_toks]
                    cora_tokens.append(CoraToken(parsed_token, dipl_tokens, anno_tokens))
                    
                elif isinstance(chunk, tokenizer.Newline):
                    pass

                elif isinstance(chunk, tokenizer.Whitespace):
                    pass

                elif isinstance(chunk, tokenizer.ShiftTagOpen):
                    open_shifttags.append(chunk.type)
                    
                elif isinstance(chunk, tokenizer.ShiftTagClose):
                    closed_shifttag = open_shifttags.pop()
                    shifttags.append(ShiftTag(closed_shifttag, shifttag_stack))
                    if not open_shifttags:
                        shifttag_stack = list()
                        
            #Parse error: return an empty token.
            except parser.ParseError as e:
                logging.error("Token could not be parsed: " + chunk.string + " Message: " + e.message)
                trans_valid = False
                cora_tokens.append(CoraToken(None, [], []))

        if trans_valid:
            if open_shifttags:
                logging.warning("Shifttag {0} not closed.".format(open_shifttags))
            return (cora_tokens, shifttags)
        else:
            return (None, None)

    def _assign_dipls_to_lines(self, transcription, cora_tokens):
        
        success = True
        
        #Assign dipl tokens to lines
        #[[dipl1_line1, dipl2_line1, ...], [dipl1_line2, ...], ...]
        c = 0
        d = 0
        lines = [line.split() for line in transcription.split("\n")]
        dipls_per_line = list()
        for line in lines:
            for index, token in enumerate(line):
                #Create a new line.
                if index == 0:
                    dipls_per_line.append(list())

                #Skip Tokens that are not CoraTokens (and thus don't have dipls).
                if not type(cora_tokens[c]) is CoraToken:
                    c += 1
                    d = 0
                    continue

                token_trans = token
                dipl_trans = str(cora_tokens[c].tok_dipls[d])
                
                #If the dipl token matches the transcription:
                if dipl_trans == token_trans:
                    dipls_per_line[-1].append(cora_tokens[c].tok_dipls[d])
                    d += 1

                #If the dipl token is included in the transcription
                #(e.g. 'ursten#' in 'ursten#de'):
                elif dipl_trans in token_trans:

                    #Get all dipls coresponding to the transcription.
                    while d < len(cora_tokens[c].tok_dipls) and dipl_trans in token_trans:
                        token_trans = token_trans.replace(dipl_trans, "", 1)
                        dipls_per_line[-1].append(cora_tokens[c].tok_dipls[d])
                        d += 1
                        if d < len(cora_tokens[c].tok_dipls):
                            dipl_trans = str(cora_tokens[c].tok_dipls[d])

                #If the dipl token is not corresponding to the transcription:
                else:
                    logging.error("Dipl token {0} is not identical to input: {1}".format(str(cora_tokens[c].tok_dipls[d]), token))
                    d += 1
                    success = False
                    
                if d > len(cora_tokens[c].tok_dipls)-1:
                    c += 1
                    d = 0

        if success:
            return dipls_per_line
        else:
            return None

    def _create_pages(self, dipls_per_line, structure, cora_tokens):

        success = True
        
        #Create pages, columns and lines with dipls.
        #While doing this get annotation information for each anno token.
        c = 0
        a = 0
        line_index = 0
        pages = []
        
        for page in structure:
            pages.append(Page(page[0][0], page[0][1], list()))
            for column in page[1]:
                pages[-1].columns.append(Column(list(), column[0]))
                for line in column[1]:
                    try:
                        pages[-1].columns[-1].lines.append(Line(line[0], dipls_per_line[line_index]))
                    except IndexError:
                        logging.error("Did not find line {0}.".format(line_index))
                        line_index += 1
                        continue
                    
                    #Get annotation from Bonn token.
                    for bonn_token in line[1]:
                         
                        #Skip Tokens that are not CoraTokens.
                        if not type(cora_tokens[c]) is CoraToken:
                            c += 1
                            a = 0
                            continue

                        #For comparison of transcription and anno tokens
                        #remove | and/or linebreak indicators like (=)| etc.
                        bonn_trans = re.sub(r"(\|*[\(<]*=[\)>]*\|*|\|+)", "", bonn_token.find("form").attrib["trans"])
                        anno_trans = re.sub(r"(\|*[\(<]*=[\)>]*\|*|\|+)", "", str(cora_tokens[c].tok_annos[a]))
                        
                        #If Bonn and anno token are identical:
                        if anno_trans == bonn_trans:
                            cora_tokens[c].tok_annos[a] = self._get_annotation(cora_tokens[c].tok_annos[a], bonn_token)
                            a += 1
                            
                        #If the Bonn token contains the anno token:
                        elif anno_trans in bonn_trans:
                            #Get all anno tokens corresponding to this Bonn token.
                            while a < len(cora_tokens[c].tok_annos) and anno_trans in bonn_trans:
                                bonn_trans = bonn_trans.replace(anno_trans, "", 1)
                                #Do not annotate punctuation marks.
                                if re.search(r"\w", str(cora_tokens[c].tok_annos[a])):
                                    cora_tokens[c].tok_annos[a] = self._get_annotation(cora_tokens[c].tok_annos[a], bonn_token)
                                a += 1
                                if a < len(cora_tokens[c].tok_annos):
                                    anno_trans = re.sub(r"(\|*[\(<]*=[\)>]*\|*|\|+)", "", str(cora_tokens[c].tok_annos[a]))

                        #If the anno token does not match the Bonn token:
                        else:
                            logging.error("Anno token {0} is not identical to input {1}.".format(str(cora_tokens[c].tok_annos[a]), \
                                                                                                 bonn_token.find("form").attrib["trans"]))
                            a += 1
                            success = False
                            
                        if a > len(cora_tokens[c].tok_annos)-1:
                            c += 1
                            a = 0
                            
                            
                    line_index += 1
        if success:
            return pages
        else:
            return None
    
    def import_from_file(self, filename):

        self.valid_document = True

        #Read in BonnXML file and create ElementTree.
        try:
            tree = ET.parse(filename, ET.XMLParser())
        except:
            logging.error("Cannot parse file {0}. Message: {1}".format(filename, e.message))
            return None
        root = tree.getroot()

        sigle = ""
        name = ""

        #Get the element containing the header.
        header_element = root.find("header")

        #Create CoraXML header
        #and get sigle and name values.
        if header_element is not None:
            sigle = header_element.find("general/id").attrib["val"]
            name = header_element.find("general/abbreviation").attrib["ab_ddd"]
            header = self._create_header(header_element, output="dict")
            header_string = self._create_header(header_element, output="string")
        else:
            header = dict()
            header_string = ""
            logging.error("No header!")

        #Reset ID counters
        Page.id_counter.clear()
        Column.id_counter.clear()
        Line.id_counter.clear()
        CoraToken.id_counter.clear()
        TokDipl.id_counter.clear()
        TokAnno.id_counter.clear()
        
        pages = []
        tokens = []
        shifttags = []

        #Get structure of the BonnXML
        structure = self._get_structure_of_bonn_xml(root)

        #Get transcription
        #with tokens separated by spaces
        #and lines indicated by \n
        transcription = self._get_transcription_from_bonn_xml(structure)

        #Preprocess transcription
        transcription = self._preprocess_transcription(transcription)

        #Tokenize transcription
        #Remove whitespace tokens
        tokenized_input = [chunk for chunk in self.tokenizer.tokenize(transcription) \
                           if not isinstance(chunk, tokenizer.Whitespace)]

        #Create cora tokens.
        (cora_tokens, shifttags) = self._create_cora_tokens(tokenized_input)
        if not cora_tokens:
            logging.error("XML cannot be parsed.")
            return None
        
        #Assign dipl tokens to lines.
        dipls_per_line = self._assign_dipls_to_lines(transcription, cora_tokens)
        if not dipls_per_line:
            logging.error("XML cannot be parsed.")
            return None
        
        #Create pages, columns and lines with dipls.
        #While doing this get annotation information for each anno token.
        pages = self._create_pages(dipls_per_line, structure, cora_tokens)
        if not pages:
            logging.error("XML cannot be parsed.")
            return None
        
        #Create a document object.
        doc = Document(sigle, name, header, pages, cora_tokens, shifttags, header_string)

        #Return the document object.
        return doc

