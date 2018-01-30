
import logging

from lxml import etree
from coraxml_utils.coralib import *

try:
    from lxml import etree as ET
except ImportError:
    import xml.etree.ElementTree as ET

def create_exporter(format="coraxml", options=None):
    if format == "coraxml":
        return CoraXMLExporter(options)
    elif format == "trans":
        return TransExporter()
    elif format == "gatejson":
        return GateJsonExporter()
    else:
        logging.error("No valid exporter selected")


class CoraXMLExporter:

    def __init__(self, options=None):

        if options is None:
            options = dict()

        self.dipl_tag = options.get('dipl_tag_name', "dipl")
        self.anno_tag = options.get('anno_tag_name', "mod")
        self.simple_attrib = options.get('simple_attrib_name', "ascii")

    def _create_xml_token(self, tok):

        tok_xml = ET.Element("token", {"id": tok.id,
                                       "trans": tok.trans.trans()})

        for dipl in tok.tok_dipls:
            dipl_xml = ET.SubElement(tok_xml, self.dipl_tag,
                                     {"id": dipl.id, 
                                      "trans": dipl.trans.trans()})
            dipl_xml.set("utf", dipl.trans.utf())
        for mod in tok.tok_annos:
            mod_xml = ET.SubElement(tok_xml, self.anno_tag,
                                       {"id": mod.id,
                                        "trans": mod.trans.trans()})
            mod_xml.set("utf", mod.trans.utf())
            mod_xml.set(self.simple_attrib, mod.trans.simple())

            if mod.checked:
                mod_xml.set("checked", "y")

            for key, val in mod.tags.items():
                ET.SubElement(mod_xml, key, {"tag": val})

            for val in mod.flags:
                ET.SubElement(mod_xml, "cora-flag", {"name": val})

        return tok_xml

    def export(self, doc):

        root = ET.Element("text")
        root.set("id", doc.sigle)
        header = ET.SubElement(root, "header")
        ## TODO improve export of the header    
        if doc.header_string:
            headerxmlstr = ET.fromstring(doc.header_string)
            header.append(headerxmlstr)
        else:
            header.text = "\n".join(key + ":" + value for key, value in doc.header)
    

        layoutinfo = ET.SubElement(root, "layoutinfo")
        for page in doc.pages:
            page_xml = ET.Element("page", {"id": page.id,
                                           "no": page.name,
                                           "range": page.range()})
            if page.side:
                page_xml.set("side", page.side)

            layoutinfo.append(page_xml)

            for col in page.columns:
                col_xml = ET.Element("column", {"id": col.id,
                                                "range": col.range()})
                if col.name:
                    col_xml.set("name", col.name)
                layoutinfo.append(col_xml)

                for line in col.lines:
                    # empty lines could come about after double dashes at
                    # line end have been resolved
                    if line:
                        line_xml = ET.Element("line", {"id": line.id,
                                                       "name": line.name,
                                                       # "loc": self.loc(),
                                                       "range": line.range()})
                    layoutinfo.append(line_xml)

        shifttags = ET.SubElement(root, "shifttags")
        for shifttag in doc.shifttags:
            ET.SubElement(shifttags, shifttag.tag(), {"range": shifttag.range()})

        for token_or_comment in doc.tokens:
            if isinstance(token_or_comment, CoraToken):
                root.append(self._create_xml_token(token_or_comment))

            elif isinstance(token_or_comment, CoraComment):
                comment = token_or_comment
                comm_xml = ET.Element("comment", {"type": comment.type})
                comm_xml.text = comment.content
                root.append(comm_xml)
            else:
                raise ValueError("found something weird in this document's token list")

        return  ET.ElementTree(root)


class TransExporter:

    def __init__(self):
        pass

    def export(self, doc):

        # list of strings to be joined at end of method
        output = list()

        output.append("+H")
        ## TODO improve export of the header
        if doc.header_string:
            output.append(doc.header_string)
        else:
            for key, value in doc.header:
                output.append(key + ':' + value)
        output.append("@H")

        for p in doc.pages:
            for c in p.columns:
                for l in c.lines:
                    for d in l.dipls:
                        tok = d.get_token() # ??
                        
                        
def print_file(self):
    if self.options.bibinfo == "both":
        print(*self.header, sep="\n", file=self.outfile)
        # print(file=self.outfile)  # empty line after header

    join_char = "\n" if self.options.taggermode else " "

    for l in self.text:
        line = [x for x in l["line"].split(" ") if x]
        if self.options.bibinfo in {"both", "line"}:
            bibstr = l["bibl"] + "\t"
        else:
            bibstr = ""

        if line:
            print(bibstr + join_char.join(line).strip(), file=self.outfile)


class GateJsonExporter:

    def __init__(self):
        pass

    def export(self, doc):

        json_object = {
            'text': '',
            'entities': {
                'Layout:Page': [],
                'Layout:Column': [],
                'Layout:Line': [],
                'Token:Cora': [],
                'Token:Dipl': [],
                'Token:Anno': [],
                'Token:Comment': []
            }
        }

        ## add metadata
        json_object['sigle'] = doc.sigle
        json_object['name'] = doc.name
        json_object['header'] = doc.header

        page_beginnings = {}
        page_ends = {}
        for page in doc.pages:
            page_beginnings[page.columns[0].lines[0].dipls[0]._id] = page
            page_ends[page.columns[-1].lines[-1].dipls[-1]._id] = page

        column_beginnings = {}
        column_ends = {}
        for column in [column for page in doc.pages for column in page.columns]:
            column_beginnings[column.lines[0].dipls[0]._id] = column
            column_ends[column.lines[-1].dipls[-1]._id] = column

        line_beginnings = {}
        line_ends = {}
        for line in [line for page in doc.pages for column in page.columns for line in column.lines]:
            line_beginnings[line.dipls[0]._id] = line
            line_ends[line.dipls[-1]._id] = line

        shifttag_beginnings = {}
        for shifttag in doc.shifttags:
            if shifttag.tokens[0]._id not in shifttag_beginnings:
                shifttag_beginnings[shifttag.tokens[0]._id] = []
            shifttag_beginnings[shifttag.tokens[0]._id].append(shifttag)
        open_shifttags = {}

        char_offset = 0
        last_dipl_token_offset = None
        last_anno_token_offset = None
        last_page_offset = None
        last_column_offset = None
        last_line_offset = None

        for token in doc.tokens:
            if isinstance(token, CoraToken):

                tok_annos = list(token.tok_annos)
                tok_annos.reverse()

                tok_dipls = list(token.tok_dipls)
                tok_dipls.reverse()

                ## CoraToken will start with a dipl token - so add 1 to curr char offset
                ## (unless we are at the beginning of the text)
                last_cora_token_offset = char_offset + 1 if char_offset > 0 else char_offset
                if token._id in shifttag_beginnings:
                    for shifttag in shifttag_beginnings[token._id]:
                        if shifttag.tokens[-1]._id not in open_shifttags:
                            open_shifttags[shifttag.tokens[-1]._id] = []
                        open_shifttags[shifttag.tokens[-1]._id].append((char_offset + 1 if char_offset > 0 else char_offset, shifttag))

                for token_char in token.trans.get_parse_with_tokenization():
                    if token_char['type'] == 'token_begin':
                        if 'dipl_id' in token_char:
                            ## add linebreak or whitespace
                            if token_char['dipl_id'] in line_beginnings:
                                if last_line_offset is not None: ## ignore first linebreak
                                    json_object['text'] += '\n'
                                    char_offset += 1
                                last_line_offset = char_offset
                            else:
                                json_object['text'] += ' '
                                char_offset += 1

                            if token_char['dipl_id'] in page_beginnings:
                                last_page_offset = char_offset

                            if token_char['dipl_id'] in column_beginnings:
                                last_column_offset = char_offset

                            ## update last dipl offset
                            last_dipl_token_offset = char_offset

                        if 'anno_id' in token_char:
                            last_anno_token_offset = char_offset

                    elif token_char['type'] == 'token_end':

                        if 'dipl_id' in token_char:
                            ## add page annotation
                            if token_char['dipl_id'] in page_ends:
                                json_object['entities']['Layout:Page'].append(
                                    {
                                        'indices': [last_page_offset, char_offset],
                                        'id': page_ends[token_char['dipl_id']].id,
                                        'name': page_ends[token_char['dipl_id']].name,
                                        'side': page_ends[token_char['dipl_id']].side
                                    }
                                )
                            ## add column annotation
                            if token_char['dipl_id'] in column_ends:
                                json_object['entities']['Layout:Column'].append(
                                    {
                                        'indices': [last_column_offset, char_offset],
                                        'id': column_ends[token_char['dipl_id']].id,
                                        'name': column_ends[token_char['dipl_id']].name
                                    }
                                )
                            ## add line annotation
                            if token_char['dipl_id'] in line_ends:
                                json_object['entities']['Layout:Line'].append(
                                    {
                                        'indices': [last_line_offset, char_offset],
                                        'id': line_ends[token_char['dipl_id']].id,
                                        'name': line_ends[token_char['dipl_id']].name
                                    }
                                )
                            ## add dipl token annotation
                            tok_dipl = {
                                    'indices': [last_dipl_token_offset, char_offset],
                            }
                            tok_dipl_object = tok_dipls.pop()

                            tok_dipl['trans'] = tok_dipl_object.trans.trans()
                            tok_dipl['utf'] = tok_dipl_object.trans.utf()

                            tok_dipl['id'] = tok_dipl_object.id

                            json_object['entities']['Token:Dipl'].append(tok_dipl)

                        if 'anno_id' in token_char:
                            tok_anno = {
                                    'indices': [last_anno_token_offset, char_offset],
                            }
                            tok_anno_object = tok_annos.pop()

                            tok_anno['trans'] = tok_anno_object.trans.trans()
                            tok_anno['utf'] = tok_anno_object.trans.utf()
                            tok_anno['simple'] = tok_anno_object.trans.simple()

                            tok_anno['id'] = tok_anno_object.id
                            tok_anno['checked'] = tok_anno_object.checked

                            for anno_name, anno_value in tok_anno_object.tags.items():
                                tok_anno[anno_name] = anno_value

                            tok_anno['flags'] = list(tok_anno_object.flags)

                            json_object['entities']['Token:Anno'].append(tok_anno)
                    else:
                        json_object['text'] += token_char['dipl_utf']
                        char_offset += len(token_char['dipl_utf'])

                ## add CoraToken annotation
                json_object['entities']['Token:Cora'].append(
                    {
                        'indices': [last_cora_token_offset, char_offset],
                        'id': token.id,
                        'trans': str(token.trans)
                    }
                )

                ## add shifttags
                if token._id in open_shifttags:
                    for start_offset, shifttag in open_shifttags[token._id]:
                        if 'Shifttags:' + shifttag.tag() not in json_object['entities']:
                            json_object['entities']['Shifttags:' + shifttag.tag()] = []
                        json_object['entities']['Shifttags:' + shifttag.tag()].append(
                            {
                                'indices': [start_offset, char_offset],
                                'type': shifttag.type
                            }
                        )

            elif isinstance(token, CoraComment):
                json_object['entities']['Token:Comment'].append(
                    {
                        'indices': [char_offset, char_offset],
                        'type': token.type,
                        'content': token.content
                    }
                )

        return json_object
