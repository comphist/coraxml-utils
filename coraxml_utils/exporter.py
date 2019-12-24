import logging

from lxml import etree as ET
import markdown_strings

from coraxml_utils.coralib import *
from coraxml_utils.character import *


def create_exporter(format="coraxml", options=None):
    if format == "coraxml":
        return CoraXMLExporter(options)
    elif format == "trans":
        return TransExporter()
    elif format == "gatejson":
        return GateJsonExporter()
    elif format == "tei":
        return TEIExporter()
    elif format == "md":
        return MarkdownExporter()
    else:
        logging.error("No valid exporter selected")


class CoraXMLExporter:
    def __init__(self, options=None):

        if options is None:
            options = dict()

        self.dipl_tag = options.get("dipl_tag_name", "dipl")
        self.anno_tag = options.get("anno_tag_name", "mod")
        self.simple_attrib = options.get("simple_attrib_name", "ascii")

    def _create_xml_token(self, tok):

        tok_xml = ET.Element(
            "token", {"id": tok.get_external_id(), "trans": tok.trans.trans()}
        )

        for dipl in tok.tok_dipls:
            dipl_xml = ET.SubElement(
                tok_xml,
                self.dipl_tag,
                {"id": dipl.get_external_id(), "trans": dipl.trans.trans()},
            )
            dipl_xml.set("utf", dipl.trans.utf())
        for mod in tok.tok_annos:
            mod_xml = ET.SubElement(
                tok_xml,
                self.anno_tag,
                {"id": mod.get_external_id(), "trans": mod.trans.trans()},
            )
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

        cora_header = ET.SubElement(
            root, "cora-header", {"sigle": doc.sigle, "name": doc.name}
        )

        ## TODO improve export of the header
        if doc.header_string:
            # try:
            #     header = ET.fromstring(doc.header_string)
            #     root.append(header)
            # except:
            header = ET.SubElement(root, "header")
            header.text = doc.header_string
        else:
            header = ET.SubElement(root, "header")
            header.text = "\n".join(key + ":" + value for key, value in doc.header)

        layoutinfo = ET.SubElement(root, "layoutinfo")
        for page in doc.pages:
            page_xml = ET.Element(
                "page", {"id": page.id, "no": page.name, "range": page.range()}
            )
            if page.side:
                page_xml.set("side", page.side)

            layoutinfo.append(page_xml)

            for col in page.columns:
                col_xml = ET.Element("column", {"id": col.id, "range": col.range()})
                if col.name:
                    col_xml.set("name", col.name)
                layoutinfo.append(col_xml)

                for line in col.lines:
                    # empty lines could come about after double dashes at
                    # line end have been resolved
                    if line:
                        line_xml = ET.Element(
                            "line",
                            {
                                "id": line.id,
                                "name": line.name,
                                # "loc": self.loc(),
                                "range": line.range(),
                            },
                        )
                        layoutinfo.append(line_xml)
                    else:
                        logging.warning("Empty line: " + line.get_external_id())

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

        return ET.ElementTree(root)


class TransExporter:
    def __init__(self):
        pass

    def export(self, doc, token_form="trans"):
        output = list()

        output.append("+H")
        ## TODO improve export of the header
        if doc.header_string:
            output.append(doc.header_string)
        else:
            for key, value in doc.header:
                output.append(key + ":" + value)
        output.append("@H")
        output.append("")  # space between header and text

        # tokens_and_comments = iter(doc.tokens)
        # seen_dipls = set()
        # dipls_for_nextline = list()
        # for p in doc.pages:
        #     for c in p.columns:
        #         for l in c.lines:
        #             dipls_in_this_line = {d.id for d in l.dipls}
        #             output_line = dipls_for_nextline
        #             dipls_for_nextline = list()

        #             # once we've seen all the dipls in this line
        #             # we can move on to the next one
        #             while dipls_in_this_line - seen_dipls:
        #                 current_obj = next(tokens_and_comments)
        #                 if isinstance(current_obj, CoraComment):
        #                     if token_form == "trans":
        #                         output_line.append(str(current_obj))
        #                     else:
        #                         # remove comments
        #                         pass

        #                 elif isinstance(current_obj, CoraToken):
        #                     for dipl in current_obj.tok_dipls:
        #                         if token_form == "dipl":
        #                             if dipl.id in dipls_in_this_line:
        #                                     output_line.append(dipl.trans.utf())
        #                             else:
        #                                 dipls_for_nextline.append(dipl.trans.utf())
        #                         seen_dipls.add(dipl.id)

        #                     for mod in current_obj.tok_annos:
        #                         if token_form == "anno":
        #                             output_line.append(mod.trans.simple())

        #                     if token_form == "trans":
        #                         output_line.append(str(current_obj.trans))
        #                 else:
        #                     logging.warning("Unexpected object in token list of document '%s'" % doc.sigle)

        #             bibinfo = "{sigle}-{page}{side}{col},{line}\t".format(sigle=doc.sigle,
        #                                                                   page=p.name,
        #                                                                   side=p.side,
        #                                                                   col=c.name,
        #                                                                   line=l.name)
        #             output.append(bibinfo + " ".join(output_line))

        bibinfos = list()
        for p in doc.pages:
            for c in p.columns:
                for l in c.lines:
                    bibinfos.append(
                        "{sigle}-{page}{side}{col},{line}\t".format(
                            sigle=doc.sigle,
                            page=p.name,
                            side=p.side,
                            col=c.name,
                            line=l.name,
                        )
                    )
        bibinfos_iter = iter(bibinfos)
        current_line = list()
        recent_linebreak = False

        for token_or_comment in doc.tokens:
            if isinstance(token_or_comment, CoraComment):
                if "trans" in token_form:
                    current_line.append(str(token_or_comment))

            elif isinstance(token_or_comment, CoraToken):
                output_token = list()
                for c in token_or_comment.trans.parse:
                    if not isinstance(c, LineBreak):
                        if token_form == "dipl_utf":
                            char_type = c.dipl_utf
                        elif token_form == "anno_utf":
                            char_type = c.anno_utf
                        elif token_form == "anno_simple":
                            char_type = c.anno_simple
                        else:
                            char_type = c.string

                        if c.line_break_after:
                            recent_linebreak = True
                        elif c.anno_bound and token_form.startswith("anno"):
                            # do anno tokenization
                            output_token.append(" ")

                        output_token.append(char_type)

                        if token_form.startswith("anno"):
                            if (c.anno_bound or c.token_bound) and recent_linebreak:
                                current_line.append("".join(output_token))
                                output.append(
                                    next(bibinfos_iter) + " ".join(current_line)
                                )
                                output_token = list()
                                current_line = list()
                                recent_linebreak = False
                        else:
                            if c.line_break_after:
                                current_line.append("".join(output_token))
                                output.append(
                                    next(bibinfos_iter) + " ".join(current_line)
                                )
                                output_token = list()
                                current_line = list()
                                recent_linebreak = False
                if output_token:
                    current_line.append("".join(output_token))

            else:
                logging.warning(
                    "Unexpected object in token list of document '%s'" % doc.sigle
                )

        return "\n".join(output)


class TEIExporter:
    def __init__(self):
        pass

    def _add_text(self, character):

        if not character:
            return

        if not getattr(self._current_text_element, self._current_text_attribute):
            setattr(self._current_text_element, self._current_text_attribute, "")

        setattr(
            self._current_text_element,
            self._current_text_attribute,
            getattr(self._current_text_element, self._current_text_attribute)
            + character,
        )

    def _add_element(self, element, current_parent):

        if (
            current_parent != self.tei_root or self.sent_tag is None
        ):  # and self.head_tag is None:
            current_parent.append(element)
        else:
            self.curr_part.append(element)

    ## TODO sent_tag="bound_sent" is specific for ReN
    ## TODO it is also a hack - importers should use anno_span for sentences
    def export(self, doc, sent_tag="bound_sent"):

        page = {}
        column = {}
        line = {}

        text_root = ET.Element("text")
        tei_root = ET.SubElement(text_root, "body")
        tei_root = ET.SubElement(tei_root, "ab")
        tei_doc = ET.ElementTree(text_root)

        self.tei_root = tei_root

        current_parent = tei_root

        self.sent_tag = sent_tag
        self.curr_part = []

        ## the xml element to which characters are added
        self._current_text_element = tei_root
        ## characters have to be added either to tail or to text
        self._current_text_attribute = "text"

        in_multiverbation = False

        ## get layoutinfo
        for page_object in doc.pages:
            page[page_object.columns[0].lines[0].dipls[0].get_internal_id()] = (
                page_object.name + page_object.side
            )
        for column_object in [column for page in doc.pages for column in page.columns]:
            column[
                column_object.lines[0].dipls[0].get_internal_id()
            ] = column_object.name
        for line_object in [
            line
            for page in doc.pages
            for column in page.columns
            for line in column.lines
        ]:
            line[line_object.dipls[0].get_internal_id()] = line_object.name

        open_tags = []

        for token in doc.tokens:

            if type(token) == CoraToken:

                dipl_tokens = list(token.tok_dipls)
                dipl_tokens.reverse()
                anno_tokens = list(token.tok_annos)
                anno_tokens.reverse()

                token_chars = [Char("")] + token.trans.parse + [Char("")]
                token_chars[0].anno_bound = True
                token_chars[-1].anno_bound = True

                token_chars[0].dipl_bound = True
                token_chars[-1].dipl_bound = True

                for position, char in enumerate(token_chars):

                    if char.anno_bound:
                        while current_parent.tag not in ["w", tei_root.tag]:
                            open_tags.append(
                                (current_parent.tag, current_parent.attrib)
                            )
                            current_parent = current_parent.getparent()

                        current_parent = tei_root
                        self._current_text_attribute = "tail"

                    if char.dipl_bound:

                        if dipl_tokens:
                            current_dipl = dipl_tokens.pop()

                            ## test for line
                            if current_dipl.get_internal_id() in line:

                                ## test for column
                                if current_dipl.get_internal_id() in column:

                                    ## test for page
                                    if current_dipl.get_internal_id() in page:
                                        ## add page
                                        self._add_element(
                                            ET.Element(
                                                "pb",
                                                n=page[current_dipl.get_internal_id()],
                                            ),
                                            current_parent,
                                        )

                                    ## add column
                                    column_name = None
                                    if column[current_dipl.get_internal_id()]:
                                        column_name = column[
                                            current_dipl.get_internal_id()
                                        ]

                                    if column_name != "--":
                                        last_element = ET.Element("cb")
                                        self._add_element(last_element, current_parent)

                                        if column_name != None:
                                            last_element.attrib["n"] = column_name

                                ## add line
                                self._current_text_element = ET.Element(
                                    "lb", n=line[current_dipl.get_internal_id()]
                                )
                                self._add_element(
                                    self._current_text_element, current_parent
                                )
                                self._current_text_attribute = "tail"

                            ## test for univerbation without linebreak
                            elif not char.anno_bound:
                                self._current_text_element = ET.Element(
                                    "space", quantity="1", unit="chars"
                                )
                                self._add_element(
                                    self._current_text_element, current_parent
                                )
                                self._current_text_attribute = "tail"

                        else:
                            current_dipl = None

                    if char.anno_bound:

                        if not char.dipl_bound:
                            if not in_multiverbation:
                                self._curr_anno_xml.set("join", "right")
                                in_multiverbation = True
                            else:
                                self._curr_anno_xml.set("join", "both")
                        else:
                            if in_multiverbation:
                                self._curr_anno_xml.set("join", "left")
                                in_multiverbation = False

                        if anno_tokens:
                            self._curr_anno = anno_tokens.pop()
                            annotations = {
                                "{http://www.w3.org/XML/1998/namespace}id": self._curr_anno.get_external_id()
                            }  #'tok': self._curr_anno.trans.simple() }
                            if "pos" in self._curr_anno.tags:
                                annotations["pos"] = self._curr_anno.tags.get("pos")
                                if "pos_gen" in self._curr_anno.tags:
                                    annotations[
                                        "pos"
                                    ] += "<" + self._curr_anno.tags.get("pos_gen")
                            if "morph" in self._curr_anno.tags:
                                annotations["msd"] = self._curr_anno.tags.get("morph")
                            ## TODO this is specific for ren -- add option
                            if "lemma_wsd" in self._curr_anno.tags:
                                annotations["lemma"] = self._curr_anno.tags.get(
                                    "lemma_wsd"
                                )

                            self._curr_anno_xml = ET.Element("w", **annotations)
                            self._add_element(self._curr_anno_xml, tei_root)

                            current_parent = self._curr_anno_xml
                            while open_tags:
                                tag, attrib = open_tags.pop()
                                current_parent = ET.SubElement(
                                    current_parent, tag, **attrib
                                )

                            self._current_text_element = current_parent
                            self._current_text_attribute = "text"

                        else:
                            self._curr_anno = None

                        if self._curr_anno is not None:

                            curr_sent_tag = self._curr_anno.tags.get(
                                self.sent_tag, None
                            )

                            parent_node = tei_root

                            if curr_sent_tag is not None and curr_sent_tag != "None":

                                ## create new sentence node
                                parent_node = ET.SubElement(parent_node, "s")
                                if self._curr_anno.tags[self.sent_tag].startswith(
                                    "Satzteil_"
                                ):
                                    parent_node.set(
                                        "part", self._curr_anno.tags[self.sent_tag][-1]
                                    )

                            ## add elements to part
                            if (
                                curr_sent_tag is not None
                            ):  # or curr_head_tag is not None:
                                for element in self.curr_part:
                                    parent_node.append(element)
                                self.curr_part = []

                    def getPlacement(bracket_string):

                        ## ReN: continuation below or above line
                        if bracket_string.startswith("\\F"):
                            if bracket_string[2] == "U":
                                return "below"
                            elif char.string[2] == "O":
                                return "above"
                        ## ReN: paratext
                        elif char.string.startswith("*"):
                            if char.string[1] == "U":
                                return "bottom"
                            elif char.string[1] == "O":
                                return "top"
                            elif char.string[1] == "T":
                                return "inline"
                            elif char.string[1] == "L":
                                return "margin left"
                            elif char.string[1] == "R":
                                return "margin right"
                            elif char.string[1] == "I":
                                return "interlinear"

                        ## bracket string does not have a known format
                        return None

                    ## add subtoken information (like strikethrough)
                    if (
                        isinstance(char, Whitespace)
                        or isinstance(char, Multiverbation)
                        or isinstance(char, Univerbation)
                    ):
                        pass
                    elif isinstance(char, IllegibleChar):
                        self._current_text_element = ET.SubElement(
                            current_parent, "gap", reason="illegible"
                        )
                        self._current_text_attribute = "tail"
                    elif (
                        isinstance(char, Addition)
                        or isinstance(char, Correction)
                        or isinstance(char, Continuation)
                    ):
                        if char.opening:
                            current_parent = ET.SubElement(current_parent, "add")
                            placement = getPlacement(char.string)
                            if placement is not None:
                                current_parent.set("place", placement)
                            self._current_text_element = current_parent
                            self._current_text_attribute = "text"
                        else:
                            current_parent = current_parent.getparent()
                            self._current_text_attribute = "tail"
                    elif isinstance(char, Note):
                        if char.opening:
                            current_parent = ET.SubElement(current_parent, "note")
                            placement = getPlacement(char.string)
                            if placement is not None:
                                current_parent.set("place", placement)
                            self._current_text_element = current_parent
                            self._current_text_attribute = "text"
                        else:
                            current_parent = current_parent.getparent()
                            self._current_text_attribute = "tail"
                    elif isinstance(char, Recognizable):
                        if char.opening:
                            current_parent = ET.SubElement(current_parent, "unclear")
                            self._current_text_element = current_parent
                            self._current_text_attribute = "text"
                        else:
                            current_parent = current_parent.getparent()
                            self._current_text_attribute = "tail"
                    elif isinstance(char, ExpandedAbbreviation):
                        if char.opening:
                            current_parent = ET.SubElement(current_parent, "expan")
                            self._current_text_element = current_parent
                            self._current_text_attribute = "text"
                        else:
                            current_parent = current_parent.getparent()
                            self._current_text_attribute = "tail"
                    elif isinstance(char, Strikethrough):
                        if char.opening:
                            current_parent = ET.SubElement(current_parent, "del")
                            self._current_text_element = current_parent
                            self._current_text_attribute = "text"
                        else:
                            current_parent = current_parent.getparent()
                            self._current_text_attribute = "tail"
                    else:
                        self._add_text(char.string)

            elif type(token) == CoraComment:
                ## TODO what about type?
                comment_element = ET.SubElement(tei_root, "note", type="editorial")
                comment_element.text = token.content

        ## elements not assigned to a part
        if self.curr_part:
            for element in self.curr_part:
                tei_root.append(element)

        return tei_doc


class GateJsonExporter:
    def __init__(self):
        pass

    def export(self, doc):

        json_object = {
            "text": "",
            "entities": {
                "Layout:Page": [],
                "Layout:Column": [],
                "Layout:Line": [],
                "Token:Cora": [],
                "Token:Dipl": [],
                "Token:Anno": [],
                "Token:Comment": [],
            },
        }

        ## add metadata
        json_object["sigle"] = doc.sigle
        json_object["name"] = doc.name
        json_object["header"] = doc.header

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
        for line in [
            line
            for page in doc.pages
            for column in page.columns
            for line in column.lines
        ]:
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
                last_cora_token_offset = (
                    char_offset + 1 if char_offset > 0 else char_offset
                )
                if token._id in shifttag_beginnings:
                    for shifttag in shifttag_beginnings[token._id]:
                        if shifttag.tokens[-1]._id not in open_shifttags:
                            open_shifttags[shifttag.tokens[-1]._id] = []
                        open_shifttags[shifttag.tokens[-1]._id].append(
                            (
                                char_offset + 1 if char_offset > 0 else char_offset,
                                shifttag,
                            )
                        )

                current_anno = None
                current_dipl = None

                token_chars = [Char("")] + token.trans.parse + [Char("")]
                token_chars[0].anno_bound = True
                token_chars[-1].anno_bound = True

                token_chars[0].dipl_bound = True
                token_chars[-1].dipl_bound = True

                for token_char in token_chars:
                    if token_char.dipl_bound:

                        if current_dipl:
                            ## close last token
                            last_dipl = current_dipl
                            ## add page annotation
                            if last_dipl._id in page_ends:
                                json_object["entities"]["Layout:Page"].append(
                                    {
                                        "indices": [last_page_offset, char_offset],
                                        "id": page_ends[last_dipl._id].id,
                                        "name": page_ends[last_dipl._id].name,
                                        "side": page_ends[last_dipl._id].side,
                                    }
                                )
                            ## add column annotation
                            if last_dipl._id in column_ends:
                                json_object["entities"]["Layout:Column"].append(
                                    {
                                        "indices": [last_column_offset, char_offset],
                                        "id": column_ends[last_dipl._id].id,
                                        "name": column_ends[last_dipl._id].name,
                                    }
                                )
                            ## add line annotation
                            if last_dipl._id in line_ends:
                                json_object["entities"]["Layout:Line"].append(
                                    {
                                        "indices": [last_line_offset, char_offset],
                                        "id": line_ends[last_dipl._id].id,
                                        "name": line_ends[last_dipl._id].name,
                                    }
                                )
                            ## add dipl token annotation
                            tok_dipl = {
                                "indices": [last_dipl_token_offset, char_offset],
                            }
                            tok_dipl_object = last_dipl

                            tok_dipl["trans"] = tok_dipl_object.trans.trans()
                            tok_dipl["utf"] = tok_dipl_object.trans.utf()

                            tok_dipl["id"] = tok_dipl_object.id

                            json_object["entities"]["Token:Dipl"].append(tok_dipl)

                        if tok_dipls:
                            current_dipl = tok_dipls.pop()
                            ## add linebreak or whitespace
                            if current_dipl._id in line_beginnings:
                                if (
                                    last_line_offset is not None
                                ):  ## ignore first linebreak
                                    json_object["text"] += "\n"
                                    char_offset += 1
                                last_line_offset = char_offset
                            else:
                                ## TODO is this correct?
                                json_object["text"] += " "
                                char_offset += 1

                            if current_dipl._id in page_beginnings:
                                last_page_offset = char_offset

                            if current_dipl._id in column_beginnings:
                                last_column_offset = char_offset

                            ## update last dipl offset
                            last_dipl_token_offset = char_offset

                    if token_char.anno_bound:
                        ### close last token
                        if current_anno is not None:
                            tok_anno = {
                                "indices": [last_anno_token_offset, char_offset],
                            }
                            tok_anno_object = current_anno

                            tok_anno["trans"] = tok_anno_object.trans.trans()
                            tok_anno["utf"] = tok_anno_object.trans.utf()
                            tok_anno["simple"] = tok_anno_object.trans.simple()

                            tok_anno["id"] = tok_anno_object.id
                            tok_anno["checked"] = tok_anno_object.checked

                            for anno_name, anno_value in tok_anno_object.tags.items():
                                tok_anno[anno_name] = anno_value

                            tok_anno["flags"] = list(tok_anno_object.flags)

                            json_object["entities"]["Token:Anno"].append(tok_anno)

                        ### start new token
                        if tok_annos:
                            current_anno = tok_annos.pop()
                            last_anno_token_offset = char_offset

                    json_object["text"] += token_char.dipl_utf
                    char_offset += len(token_char.dipl_utf)

                ## add CoraToken annotation
                json_object["entities"]["Token:Cora"].append(
                    {
                        "indices": [last_cora_token_offset, char_offset],
                        "id": token.id,
                        "trans": str(token.trans),
                    }
                )

                ## add shifttags
                if token._id in open_shifttags:
                    for start_offset, shifttag in open_shifttags[token._id]:
                        if "Shifttags:" + shifttag.tag() not in json_object["entities"]:
                            json_object["entities"]["Shifttags:" + shifttag.tag()] = []
                        json_object["entities"]["Shifttags:" + shifttag.tag()].append(
                            {
                                "indices": [start_offset, char_offset],
                                "type": shifttag.type,
                            }
                        )

            elif isinstance(token, CoraComment):
                json_object["entities"]["Token:Comment"].append(
                    {
                        "indices": [char_offset, char_offset],
                        "type": token.type,
                        "content": token.content,
                    }
                )

        return json_object


class MarkdownExporter:
    def __init__(self):
        pass

    def export(self, doc):

        ## export as markdown
        ## uses to the pandoc extensions pipe_tables, inline_notes and strikeout

        page = {}
        column = {}

        ## get page and column info
        for page_object in doc.pages:
            page[page_object.columns[0].lines[0].dipls[0].get_internal_id()] = (
                page_object.name + page_object.side
            )
        for column_object in [column for page in doc.pages for column in page.columns]:
            column[
                column_object.lines[0].dipls[0].get_internal_id()
            ] = column_object.name

        page_name = ""
        column_name = ""

        last_header_line = (
            ":-----|:------------------------------------------------------------------"
        )
        output = ["% " + doc.name, "", "|", last_header_line]

        current_line = []

        for token in doc.tokens:
            if isinstance(token, CoraComment):

                # converts comment to pandoc markdowns inline footnote
                ## TODO handle square brackets in comments
                assert "]" not in token.content
                comment = "^[" + markdown_strings.esc_format(token.content) + "]"

                ## add to current_line - if current_line is empty: add to last line in output
                ## (except for at the beginning)
                if current_line:
                    current_line.append(comment)
                else:
                    if output[-1] == last_header_line:
                        current_line.append(comment)
                    else:
                        output[-1] += " " + comment
            else:
                for dipl in token.tok_dipls:

                    if dipl.get_internal_id() in page:
                        page_name = page[dipl.get_internal_id()]
                    if dipl.get_internal_id() in column:
                        column_name = column[dipl.get_internal_id()]
                        if column_name is None or column_name == "--":
                            column_name = ""

                    current_line.append(
                        markdown_strings.esc_format(
                            dipl.trans
                            ## mark expansions, paratext and strikethrough with markdown (strikethrough uses pandocs markdown)
                            .transform(
                                lambda c: ExpandedAbbreviation("*", dipl_utf="*"),
                                lambda c: isinstance(c, ExpandedAbbreviation),
                            )
                            .transform(
                                lambda c: Para("**", dipl_utf="**"),
                                lambda c: isinstance(c, Para),
                            )
                            .transform(
                                lambda c: Strikethrough("~~", dipl_utf="~~"),
                                lambda c: isinstance(c, Strikethrough),
                            )
                            ## TODO the following transformations are specific for ReN
                            ## this should be changed to be usable for other corpora as well
                            .transform(
                                lambda c: Multiverbation("", dipl_utf=""),
                                lambda c: isinstance(c, Multiverbation),
                            )
                            .transform(
                                lambda c: Univerbation("", dipl_utf=""),
                                lambda c: isinstance(c, Univerbation),
                            )
                            .transform(
                                lambda c: Recognizable("[", dipl_utf="["),
                                lambda c: isinstance(c, Recognizable) and c.opening,
                            )
                            .transform(
                                lambda c: Recognizable("]", dipl_utf="]"),
                                lambda c: isinstance(c, Recognizable) and not c.opening,
                            )
                            .transform(
                                lambda c: IllegibleChar("[…]", dipl_utf="[…]"),
                                lambda c: isinstance(c, IllegibleChar)
                                or (isinstance(c, TextChar) and c.dipl_utf == "…"),
                            )
                            .transform(
                                lambda c: Lacuna("^[Lücke]", dipl_utf="^[Lücke]"),
                                lambda c: isinstance(c, Lacuna),
                            )
                            .transform(
                                lambda c: Continuation("", dipl_utf=""),
                                lambda c: isinstance(c, Continuation),
                            )
                            .trans()
                        )
                    )

                    if doc.is_end_of_line(dipl):
                        bibinfo = (
                            page_name
                            + column_name
                            + ","
                            + doc.get_line_for_dipl(dipl).name
                        )

                        output.append(bibinfo + " | " + " ".join(current_line))
                        current_line = []

        return "  \n".join(output)
