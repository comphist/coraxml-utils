import logging
from collections import defaultdict

from coraxml_utils.coralib import *
import coraxml_utils.parsed_token as parsed_token

try:
    from lxml import etree as ET
except ImportError:
    import xml.etree.ElementTree as ET


def create_importer(file_format, dialect=None):

    if file_format == 'CorA-XML':
        cora_importer = CoraXMLImporter()
        if dialect is None:
            pass
        elif dialect == 'rem':
            cora_importer.tok_dipl_tag = 'tok_dipl'
            cora_importer.tok_anno_tag = 'tok_anno'
            cora_importer.tokenparser = parsed_token.RemToken
        else:
            raise ValueError("CorA-XML dialect " + dialect + " is not supported.")
        return cora_importer
    elif file_format == "trans":
        if dialect == "ref":
            return TransImporter(parsed_token.RefToken)
        elif dialect == "redi":
            return TransImporter(parsed_token.RediToken)
        else:
            return TransImporter(parsed_token.PlainToken)
    else:
        raise ValueError("File format " + file_format + " is not supported.")

class CoraXMLImporter:

    def __init__(self):
        self.tok_dipl_tag = 'dipl'
        self.tok_anno_tag = 'mod'
        self.tokenparser = parsed_token.PlainToken


    def _create_dipl_token(self, dipl_element):
        return TokDipl(self.tokenparser(dipl_element.attrib['trans']), extid=dipl_element.attrib['id'])

    def _create_anno_token(self, anno_element):

        # retrieve annotations
        tags = dict()
        flags = set()

        for annotation_element in anno_element:

            if annotation_element.tag == 'cora-flag':
                flagname = annotation_element.attrib['name']
                if flagname in flags:
                    logging.warning('Flag ' + flagname + ' is set twice for anno-token ' + anno_element.attrib['id'] + '.')
                flags.add(flagname)
            else:
                tagname = annotation_element.tag
                if tagname in tags:
                    logging.warning('Tag ' + tagname + ' is set twice for anno-token ' + anno_element.attrib['id'] + '.')
                tags[tagname] = annotation_element.attrib['tag']

        ## the attribute checked is not obligatory
        checked = 'checked' in anno_element.attrib and anno_element.attrib['checked'] == 'y'

        return TokAnno(
            self.tokenparser(anno_element.attrib['trans']),
            tags=tags, flags=flags, checked=checked, extid=anno_element.attrib['id']
        )

    def _create_cora_token(self, coratoken_element):

        dipl_tokens = []
        anno_tokens = []

        for dipl_element in coratoken_element.findall(self.tok_dipl_tag):
            dipl_tokens.append(self._create_dipl_token(dipl_element))
        for anno_element in coratoken_element.findall(self.tok_anno_tag):
            anno_tokens.append(self._create_anno_token(anno_element))

        parsed_token = self.tokenparser(coratoken_element.attrib['trans'])
        return CoraToken(parsed_token, dipl_tokens, anno_tokens, extid=coratoken_element.attrib['id'])

    def _get_range(self, element):
        return element.attrib['range'].split('..')

    def _connect_with_layout_elements(self, root, layout_type, subelements, subelement_type, extract_from_xml, create_object):
        """Connects elements like lines with higher element like columns.

        Positional arguments:
        root -- the xml object
        layout_type -- type of the layout element (line, column or page)
        subelement -- list of the elements that should be connected
        subelement_type -- the name of the subelement (used for warnings)
        extract_from_xml -- a function that gets the xml element and returns a dictionary with all relevant information for the layout element
        create_object -- a function that gets the dictionary from extract_from_xml with added "subelements" and returns an object representing the layout element
        """
        layout_elements = []

        # get layoutinfo from xml
        beginnings = dict()
        for element in root.findall("layoutinfo/" + layout_type):
            range = self._get_range(element)
            if range[0] in beginnings:
                logging.error('Two ' + layout_type + 's that start at the same position: ' + element.attrib['id'] + ' and ' + beginnings[range[0]]['extid'])
            beginnings[range[0]] = {**extract_from_xml(element), 'end': range[-1], 'subelements': []}

        open_element = None
        for subelement in subelements:
            if open_element is None:
                if subelement.id in beginnings:
                    open_element = beginnings.pop(subelement.id)
                else:
                    # warn and continue
                    logging.warn(subelement_type + ' that is not connected to anything in the layout: ' + subelement.id)
                    continue

            open_element['subelements'].append(subelement)
            if open_element['end'] == subelement.id:
                layout_elements.append(create_object(open_element))
                open_element = None

        if beginnings:
            logger.warn('Dropped ' + layout_type + '(s) starting with nonexistent ' + subelement_type + ': ' + str(list(beginnings.keys())))
        if open_element:
            logger.warn('Dropped ' + layout_type + '(s) ending with nonexistent ' + subelement_type + ': ' + open_element['extid'])

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
                              lambda element: {'extid': element.attrib['id'], 'name': element.attrib['no'], 'side': element.attrib['side']},
                              lambda dictionary: Page(dictionary['name'], dictionary['side'], dictionary['subelements'], extid=dictionary['extid']))
        ## collect document information and create Document object
        cora_header = root.find('cora-header')

        # get header
        header_element = root.find("header")
        if not list(header_element):
            # header is only text
            header = ET.tostring(header_element, encoding="unicode", method="text")
        else:
            # header is structured as xml - keep ET.Element
            header = header_element

        return Document(cora_header.attrib['sigle'], cora_header.attrib['name'], header, pages, tokens, shifttags)


class TransImporter:

    def __init__(self, parser):
        self.ParsedToken = parser

    def import_from_string(self, intext):

        name = str()  # ???
        pages = list()
        columns = list()
        lines = list()
        tokens = list()
        shifttags = list()

        text = list()

        # read header
        header_open = False
        header_lines = list()

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

        headertext = "\n".join(header_lines)
        sigle = re.search(r"[^:\s]:\s+([\w\d]+)", headertext).group(1)

        this_line = None
        this_col = None
        this_page = None
        last_page = None
        last_side = None
        last_col = None
        last_line = None        
        in_comment = False
        open_shifttags = list()
        comment_stack = list()
        shifttag_stack = list()
        join_next_mods = False
        join_next_dipls = False

        # these need to be saved up, so they can be used when
        # the column or page changes to make new column or
        # page objects
        line_stack = list()
        column_stack = list()

        for line in text:
            this_line_dipls = list()

            bibinfo, content, *_ = line.strip().split("\t")
            if _: logging.warning("extraneous tab in line: " + line)
            for match in BIBINFO_FORMAT.findall(bibinfo):
                _, pageno, side, col, linename = match

                if side != last_side or pageno != last_page:
                   # new page and col
                   column_stack.append(Column(line_stack))
                   line_stack = list()
                   pages.append(Page(pageno, side, column_stack))
                   column_stack = list()

                elif col != last_col:
                    # start new col
                    # (columns started this way have names)
                    column_stack.append(Column(line_stack, name=col))
                    line_stack = list()


                last_page = pageno
                last_side = side
                last_col = col

            for tok in content.split():
                # shifttags
                if re.match(r"\+[FLRÜMQ]p?", tok):
                    open_shifttags.append(tok[1:])
                elif re.match(r"@([FLRÜMQ]p?)", tok):
                    closed_shifttag = open_shifttags.pop()
                    shifttags.append(ShiftTag(closed_shifttag, shifttag_stack))
                    if not open_shifttags:
                        shifttag_stack = list()

                # comments
                elif re.match(r"\+[KEZ]", tok):
                  in_comment = True
                elif re.match(r"@([KEZ])", tok):
                  in_comment = False
                  tokens.append(CoraComment(tok[1], comment_stack))
                  comment_stack = list()

                # tokens
                else:
                    if in_comment:
                        comment_stack.append(tok)
                    else:
                        new_token = self.ParsedToken(tok)
                        my_tok_dipls = list()
                        my_tok_annos = list()

                        # put edition numbering in comments
                        if new_token.parse[0]["type"] == "edit":
                            tokens.append(CoraComment("Z", [tok]))
                            continue

                        for new_dipl in new_token.tokenize_dipl():
                            d = TokDipl(new_dipl)
                            my_tok_dipls.append(d)
                            this_line_dipls.append(d)

                        for new_anno in new_token.tokenize_anno():
                            my_tok_annos.append(TokAnno(new_anno))

                        t = CoraToken(new_token, my_tok_dipls, my_tok_annos)
                        if join_next_mods or join_next_dipls:
                            i = -1
                            while i > -10:  # arbitrary limit on number of intervening comments
                                if isinstance(tokens[i], CoraComment):
                                    i -= 1
                                else:
                                    tokens[i].merge_token(t, join_next_dipls, join_next_mods)
                                    break
                            join_next_mods = False
                            join_next_dipls = False
                        else:
                            tokens.append(t)
                            if open_shifttags:
                                shifttag_stack.append(t)
                        
                        if new_token.parse:
                            join_next_mods = new_token.parse[-1]["char"] in {"(=)", "="}
                            join_next_dipls = new_token.parse[-1]["char"] in {"=|"}

            # at end of line 
            line_stack.append(Line(linename, this_line_dipls))

        return Document(sigle, name, headertext, pages, tokens, shifttags)