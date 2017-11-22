import logging

from coraxml_utils.coralib import *

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
        else:
            raise ValueError("CorA-XML dialect " + dialect + " is not supported.")
        return cora_importer
    else:
        raise ValueError("File format " + file_format + " is not supported.")

class CoraXMLImporter:

    def __init__(self):
        self.tok_dipl_tag = 'dipl'
        self.tok_anno_tag = 'mod'


    def _create_dipl_token(self, dipl_element):
        return TokDipl(dipl_element.attrib['id'], dipl_element.attrib['trans'])

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
            anno_element.attrib['id'], anno_element.attrib['trans'],
            tags, flags, checked
        )

    def _create_cora_token(self, coratoken_element):

        dipl_tokens = []
        anno_tokens = []

        for dipl_element in coratoken_element.findall(self.tok_dipl_tag):
            dipl_tokens.append(self._create_dipl_token(dipl_element))
        for anno_element in coratoken_element.findall(self.tok_anno_tag):
            anno_tokens.append(self._create_anno_token(anno_element))

        return CoraToken(coratoken_element.attrib['id'], coratoken_element.attrib['trans'], dipl_tokens, anno_tokens)

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


# # von transkription

#  def __init__(self, intext):
#         self.pages = list()
#         self.columns = list()
#         self.lines = list()
#         self.tokens = list()
#         self.shifttags = list()

#         self.text = list()

#         # read header
#         header_open = False
#         header_lines = list()

#         for line in intext.splitlines():
#             if line.strip() == "+H":
#                 header_open = True
#             elif line.strip() == "@H":
#                 header_open = False
#             elif header_open:
#                 header_lines.append(line)
#             elif line and not header_open:
#                 self.text.append(line)
#             else:
#                 # skip empty lines
#                 pass

#         if not header_lines:
#             raise Exception("ERROR: Header is empty!")

#         self.headertext = "\n".join(header_lines)
#         self.sigle = re.search(r"[^:\s]:\s+([\w\d]+)", self.headertext).group(1)

#         this_line = None
#         this_col = None
#         this_page = None
#         last_page = None
#         last_side = None
#         last_col = None
#         last_line = None        
#         in_comment = False
#         open_shifttags = list()
#         comment_stack = list()
#         shifttag_stack = list()
#         join_next_mods = False
#         join_next_dipls = False
#         for line in self.text:

#             bibinfo, content, *_ = line.strip().split("\t")
#             if _: print("WARNING   extraneous tab in line:", line)
#             for match in BIBINFO_FORMAT.findall(bibinfo):
#                 sigle, pageno, side, col, linename = match
#                 this_line = Line(linename, loc=match[1:])

#                 if side != last_side or pageno != last_page:
#                    # new page and col
#                    this_col = Column(col)
#                    this_col.lines.append(this_line)
#                    this_page = Page(pageno, side)
#                    this_page.columns.append(this_col)

#                    self.pages.append(this_page)
#                    self.columns.append(this_col)
#                    self.lines.append(this_line)
#                 elif col != last_col:
#                     # start new col
#                     # (columns started this way have names)
#                     this_col = Column(col)
#                     this_col.lines.append(this_line)
#                     this_page.columns.append(this_col)

#                     self.columns.append(this_col)
#                     self.lines.append(this_line)
#                 else:
#                     self.lines.append(this_line)
#                     this_col.lines.append(this_line)

#                 last_page = pageno
#                 last_side = side
#                 last_col = col

#             for tok in content.split():
#                 # shifttags
#                 if re.match(r"\+[FLRÜMQ]p?", tok):
#                     open_shifttags.append(tok[1:])
#                 elif re.match(r"@([FLRÜMQ]p?)", tok):
#                     closed_shifttag = open_shifttags.pop()
#                     self.shifttags.append(ShiftTag(closed_shifttag, shifttag_stack))
#                     if not open_shifttags:
#                         shifttag_stack = list()

#                 # comments
#                 elif re.match(r"\+[KEZ]", tok):
#                   in_comment = True
#                 elif re.match(r"@([KEZ])", tok):
#                   in_comment = False
#                   self.tokens.append(Comment(tok[1], comment_stack))
#                   comment_stack = list()

#                 # tokens
#                 else:
#                     if in_comment:
#                         comment_stack.append(tok)
#                     else:
#                         new_token = Token(tok)
#                         mtok = ParsedToken(tok, Options())

#                         if not mtok.parse:
#                             raise Exception("token has empty parse: " + tok)

#                         # put edition numbering in comments
#                         if mtok.parse[0]["type"] == "edit":
#                             self.tokens.append(Comment("Z", [tok]))
#                             continue

#                         dtrans = str(mtok.with_opts(DIPL_TRANS_OPTS).tokenize()).split()
#                         dutfs = str(mtok.with_opts(DIPL_UTF_OPTS).tokenize()).split()
#                         mtrans = str(mtok.with_opts(MOD_TRANS_OPTS).tokenize()).split()
#                         mutfs = str(mtok.with_opts(MOD_UTF_OPTS).tokenize()).split()
#                         msimple = str(mtok.with_opts(MOD_SIMPLE_OPTS).tokenize()).split()

#                         if len(dtrans) != len(dutfs):
#                             raise Exception("dipl length not equal")
#                         if len(mtrans) != len(msimple):
#                             if len(msimple) < len(mtrans):
#                                 while len(msimple) != len(mtrans):
#                                     msimple.append("")
#                             else:
#                                 raise Exception("mod length not equal")

#                         for dt, du in zip(dtrans, dutfs):
#                             new_token.dipls.append(Dipl(dt, du))

#                         for mt, mu, ms in zip(mtrans, mutfs, msimple):
#                             new_token.mods.append(Mod(mt, mu, ms))

#                         for d in new_token.dipls:
#                             this_line.tokens.append(d)

#                         if join_next_mods or join_next_dipls:
#                             i = -1
#                             while i > -10:  # arbitrary limit on number of intervening comments
#                                 if isinstance(self.tokens[i], Comment):
#                                     i -= 1
#                                 else:
#                                     self.tokens[i].merge_token(new_token, join_next_dipls, join_next_mods)
#                                     break
#                             join_next_mods = False
#                             join_next_dipls = False
#                         else:
#                             self.tokens.append(new_token)
#                             if open_shifttags:
#                                 shifttag_stack.append(new_token)
                        
#                         if mtok.parse:
#                             join_next_mods = mtok.parse[-1]["char"] in {"(=)", "="}
#                             join_next_dipls = mtok.parse[-1]["char"] in {"=|"}

#             # at end of line
#             last_line = this_line

#         self.generate_IDs()
