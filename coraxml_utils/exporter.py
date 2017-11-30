
import logging

from coraxml_utils.coralib import *
from coraxml_utils.settings import *

try:
    from lxml import etree as ET
except ImportError:
    import xml.etree.ElementTree as ET

def create_exporter(format="coraxml", dialect="ref"):
    if format == "coraxml":
        return CoraXMLExporter(dialect)
    elif format == "trans":
        return TransExporter()
    elif format == "json":
        return GateJsonExporter()
    else:
        logging.error("No valid exporter selected")


class CoraXMLExporter:

    def __init__(self, dialect):
        self.dialect = dialect
        if dialect == "rem":
            self.dipl_tag = "tok_dipl"
            self.mod_tag = "tok_anno"
        else:
            self.dipl_tag = "dipl"
            self.mod_tag = "mod"

    def _create_xml_token(self, tok):

        tok_xml = ET.Element("token", {"id": tok.id,
                                          "trans": str(tok.trans)})

        for dipl in tok.tok_dipls:
            dipl_xml = ET.SubElement(tok_xml, self.dipl_tag,
                                        {"id": dipl.id, 
                                         "trans": str(dipl.trans)})
            dipl_xml.set("utf", str(dipl.trans.to_string(character="utf")))
        for mod in tok.tok_annos:
            mod_xml = ET.SubElement(tok_xml, self.mod_tag,
                                       {"id": mod.id,
                                        "trans": str(mod.trans)})
            mod_xml.set("utf", str(mod.trans.to_string(character="utf")))
            mod_xml.set("simple", str(mod.trans.to_string(character="simple")))

            if mod.checked:
                mod_xml.set("checked", "y")

            # TODO: add annotations/flags to mod

        return tok_xml

    def export(self, doc):

        root = ET.Element("text")
        root.set("id", doc.sigle)
        header = ET.SubElement(root, "header")
        if isinstance(doc.header, str):
            header.text = doc.header
        elif isinstance(doc.header, ET.Element):
            header.append(doc.header)
        else:
            logging.warning("Found something weird in document header")

        layoutinfo = ET.SubElement(root, "layoutinfo")
        for page in doc.pages:
            page_xml = ET.Element("page", {"id": page.id,
                                              "no": page.no,
                                              "range": page.range()})
            if page.side:
                page_xml.set("side", page.side)
            layoutinfo.append(page_xml)

            for col in page.columns:
                col_xml = ET.Element("column", {"id": col.id,
                                                   "range": col.range()})
                if col.name:
                    col_xml.set("name", self.name)
                layoutinfo.append(col_xml)

                for line in col.lines:
                    # empty lines could come about after double dashes at
                    # line end have been resolved
                    if line:
                        line_xml = ET.Element("line", {"id": self.id,
                                                          "name": self.linename,
                                                          "loc": self.loc(),
                                                          "range": self.range()})
                        layoutinfo.append(line_xml)

        shifttags = ET.SubElement(root, "shifttags")
        for shifttag in doc.shifttags:
            ET.SubElement(shifttags, shifttag.tag(), {"range": shifttag.range()})

        for token_or_comment in doc.tokens:
            if isinstance(token_or_comment, CoraToken):
                root.append(self._create_xml_token(token_or_comment))

            elif isinstance(token_or_comment, Comment):
                comment = token_or_comment
                comm_xml = ET.Element("comment", {"type": comment.type})
                comm_xml.text = comment.content
                root.append(comm_xml)
            else:
                raise ValueError("found something weird in this document's token list")

        return root


class TransExporter:

    def __init__(self):
        pass

    def export(self, doc):

        # list of strings to be joined at end of method
        output = list()

        output.append("+H")
        output.append(doc.header)
        output.append("@H")

class GateJsonExporter:

    def __init__(self):
        pass

    def export(self, doc):

        ## TODO add pages, columns, shifttags, cora tokens, metadata

        json_object = {
            'text': '',
            'entities': {
                # 'Layout:Page': [],
                # 'Layout:Column': [],
                'Layout:Line': [],
                'Token:Dipl': [],
                'Token:Anno': [],
                'Token:Comment': []
            }
        }

        line_beginnings = {}
        line_ends = {}
        for line in [line for page in doc.pages for column in page.columns for line in column.lines]:
            line_beginnings[line.dipls[0]._id] = line
            line_ends[line.dipls[-1]._id] = line

        char_offset = 0
        last_dipl_token_offset = None
        last_anno_token_offset = None
        last_line_offset = None

        for token in doc.tokens:
            if isinstance(token, CoraToken):

                tok_annos = list(token.tok_annos)
                tok_annos.reverse()

                tok_dipls = list(token.tok_dipls)
                tok_dipls.reverse()

                for token_char in token.get_aligned_dipls_and_annos():
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

                            ## update last dipl offset
                            last_dipl_token_offset = char_offset

                        if 'anno_id' in token_char:
                            last_anno_token_offset = char_offset

                    elif token_char['type'] == 'token_end':

                        if 'dipl_id' in token_char:
                            ## add line annotation
                            if token_char['dipl_id'] in line_ends:
                                json_object['entities']['Layout:Line'].append(
                                    {
                                        'indices': [last_line_offset, char_offset],
                                        'name': line_ends[token_char['dipl_id']].name
                                    }
                                )
                            ## add dipl token annotation
                            tok_dipl = {
                                    'indices': [last_dipl_token_offset, char_offset],
                            }
                            tok_dipl_object = tok_dipls.pop()

                            tok_dipl['trans'] = "".join([char['trans'] for char in tok_dipl_object.trans.parse])
                            tok_dipl['utf'] = "".join([char['utf'] for char in tok_dipl_object.trans.parse])

                            tok_dipl['id'] = tok_dipl_object.id

                            json_object['entities']['Token:Dipl'].append(tok_dipl)

                        if 'anno_id' in token_char:
                            tok_anno = {
                                    'indices': [last_anno_token_offset, char_offset],
                            }
                            tok_anno_object = tok_annos.pop()

                            tok_anno['trans'] = "".join([char['trans'] for char in tok_anno_object.trans.parse])
                            tok_anno['utf'] = "".join([char['utf'] for char in tok_anno_object.trans.parse])
                            tok_anno['simple'] = "".join([char['simple'] for char in tok_anno_object.trans.parse])

                            tok_anno['id'] = tok_anno_object.id
                            tok_anno['checked'] = tok_anno_object.checked

                            for anno_name, anno_value in tok_anno_object.tags.items():
                                tok_anno[anno_name] = anno_value

                            tok_anno['flags'] = list(tok_anno_object.flags)

                            json_object['entities']['Token:Anno'].append(tok_anno)
                    else:
                        json_object['text'] += token_char['utf']
                        char_offset += len(token_char['utf'])
            elif isinstance(token, CoraComment):
                json_object['entities']['Token:Comment'].append(
                    {
                        'indices': [char_offset, char_offset],
                        'type': token.type,
                        'content': token.content
                    }
                )

        return json_object
