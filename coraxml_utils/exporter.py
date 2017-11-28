
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
                                          "trans": tok.trans})

        for dipl in tok.tok_dipls:
            dipl_xml = ET.SubElement(tok_xml, self.dipl_tag,
                                        {"id": dipl.id, 
                                         "trans": str(dipl.trans)})
            dipl_xml.set("utf", str(dipl.trans.with_opts(Options(character="utf"))))
        for mod in tok.tok_annos:
            mod_xml = ET.SubElement(tok_xml, self.mod_tag,
                                       {"id": mod.id,
                                        "trans": str(mod.trans)})
            mod_xml.set("utf", str(mod.trans.with_opts(Options(character="utf"))))
            mod_xml.set("simple", str(mod.trans.with_opts(Options(character="simple"))))

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
