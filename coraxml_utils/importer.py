import logging

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

    def doImport(self, filename):

        tree = ET.parse(filename, ET.XMLParser(remove_blank_text=True))
        root = tree.getroot()

        ## collect layout information
        pages = {}
        columns = {}
        lines = {}

        # layoutinfo = root.find("layoutinfo")
        #     layoutinfo = augment_layout_info(layoutinfo)

        # line_ends = {extract_line_end(x.get('range'))
        #              for x in root.findall('.//line')}
        # last_verb_pos = str()

        # ## TODO Header
        # header = root.find("header")
        # header = make_xml_header(header)

        ## Get shifttags
        shifttags = {}
        # insert shifttags element after header (0) and layoutinfo (1)
        # annotationspans = ET.Element("shifttags")
        # root.insert(2, annotationspans)

        ## create list of tokens and comments
        tokens = []
        for element in root:

            if element.tag == 'token':
                dipl_tokens = []
                anno_tokens = []
                ## TODO trans should not be a string but should be parsed
                for dipl_element in element.find(self.tokDipl_tag):
                    dipl_tokens.append(self._createDiplToken(dipl_element))
                for anno_element in element.find(self.tokAnno_tag):
                    pass
                tokens.append(CoraToken(element.attrib['id'], element.attrib['trans'], dipl_tokens, anno_tokens))
            elif element.tag == 'comment':
                tokens.append(CoraComment(element.attrib['type'], element.text))

        ## collect document information and create Document object
        cora_header = root.find('/text/cora-header')
        # TODO
        header = ''
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