#!/usr/bin/env python3
# coding: utf-8

import re
import argparse
from lxml import etree

from settings import *

__version__ = "2017.10.23"

DIPL_TRANS_OPTS = Options(character="orig", syllab=False, tokenize="historical",
                          illegible="original", strikethru="original",
                          doubledash="leave", preedtoken="leave")

DIPL_UTF_OPTS = Options(character="utf", syllab=False, tokenize="historical", 
                        illegible="character", strikethru="leave", 
                        doubledash="leave", preedpunc="delete", preedtoken="delete")

MOD_TRANS_OPTS = Options(character="orig", tokenize="all", 
                         illegible="original", strikethru="delete", 
                         doubledash="leave", preedtoken="leave", preedpunc="leave",
                         nosplitinit=True)

MOD_SIMPLE_OPTS = Options(character="simple", tokenize="all",  
                          illegible="leave", strikethru="delete", 
                          doubledash="delete", preedtoken="delete", preedpunc="leave",
                          nosplitinit=True)

MOD_UTF_OPTS = Options(character="utf", tokenize="all", 
                       illegible="character", strikethru="delete", 
                       doubledash="delete", preedtoken="delete", preedpunc="leave",
                       nosplitinit=True)

class Doc:

    def __init__(self, intext):
        self.pages = list()
        self.columns = list()
        self.lines = list()
        self.tokens = list()
        self.shifttags = list()

        self.text = list()

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
                self.text.append(line)
            else:
                # skip empty lines
                pass

        if not header_lines:
            raise Exception("ERROR: Header is empty!")

        self.headertext = "\n".join(header_lines)
        self.sigle = re.search(r"[^:\s]:\s+([\w\d]+)", self.headertext).group(1)

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
        for line in self.text:

            bibinfo, content, *_ = line.strip().split("\t")
            if _: print("WARNING   extraneous tab in line:", line)
            for match in BIBINFO_FORMAT.findall(bibinfo):
                sigle, pageno, side, col, linename = match
                this_line = Line(linename, loc=match[1:])

                if side != last_side or pageno != last_page:
                   # new page and col
                   this_col = Column(col)
                   this_col.lines.append(this_line)
                   this_page = Page(pageno, side)
                   this_page.columns.append(this_col)

                   self.pages.append(this_page)
                   self.columns.append(this_col)
                   self.lines.append(this_line)
                elif col != last_col:
                    # start new col
                    # (columns started this way have names)
                    this_col = Column(col)
                    this_col.lines.append(this_line)
                    this_page.columns.append(this_col)

                    self.columns.append(this_col)
                    self.lines.append(this_line)
                else:
                    self.lines.append(this_line)
                    this_col.lines.append(this_line)

                last_page = pageno
                last_side = side
                last_col = col

            for tok in content.split():
                # shifttags
                if re.match(r"\+[FLRÜMQ]p?", tok):
                    open_shifttags.append(tok[1:])
                elif re.match(r"@([FLRÜMQ]p?)", tok):
                    closed_shifttag = open_shifttags.pop()
                    self.shifttags.append(ShiftTag(closed_shifttag, shifttag_stack))
                    if not open_shifttags:
                        shifttag_stack = list()

                # comments
                elif re.match(r"\+[KEZ]", tok):
                  in_comment = True
                elif re.match(r"@([KEZ])", tok):
                  in_comment = False
                  self.tokens.append(Comment(tok[1], comment_stack))
                  comment_stack = list()

                # tokens
                else:
                    if in_comment:
                        comment_stack.append(tok)
                    else:
                        new_token = Token(tok)
                        mtok = ParsedToken(tok, Options())

                        if not mtok.parse:
                            raise Exception("token has empty parse: " + tok)

                        # put edition numbering in comments
                        if mtok.parse[0]["type"] == "edit":
                            self.tokens.append(Comment("Z", [tok]))
                            continue

                        dtrans = str(mtok.with_opts(DIPL_TRANS_OPTS).tokenize()).split()
                        dutfs = str(mtok.with_opts(DIPL_UTF_OPTS).tokenize()).split()
                        mtrans = str(mtok.with_opts(MOD_TRANS_OPTS).tokenize()).split()
                        mutfs = str(mtok.with_opts(MOD_UTF_OPTS).tokenize()).split()
                        msimple = str(mtok.with_opts(MOD_SIMPLE_OPTS).tokenize()).split()

                        if len(dtrans) != len(dutfs):
                            raise Exception("dipl length not equal")
                        if len(mtrans) != len(msimple):
                            if len(msimple) < len(mtrans):
                                while len(msimple) != len(mtrans):
                                    msimple.append("")
                            else:
                                raise Exception("mod length not equal")

                        for dt, du in zip(dtrans, dutfs):
                            new_token.dipls.append(Dipl(dt, du))

                        for mt, mu, ms in zip(mtrans, mutfs, msimple):
                            new_token.mods.append(Mod(mt, mu, ms))

                        for d in new_token.dipls:
                            this_line.tokens.append(d)

                        if join_next_mods or join_next_dipls:
                            i = -1
                            while i > -10:  # arbitrary limit on number of intervening comments
                                if isinstance(self.tokens[i], Comment):
                                    i -= 1
                                else:
                                    self.tokens[i].merge_token(new_token, join_next_dipls, join_next_mods)
                                    break
                            join_next_mods = False
                            join_next_dipls = False
                        else:
                            self.tokens.append(new_token)
                            if open_shifttags:
                                shifttag_stack.append(new_token)
                        
                        if mtok.parse:
                            join_next_mods = mtok.parse[-1]["char"] in {"(=)", "="}
                            join_next_dipls = mtok.parse[-1]["char"] in {"=|"}

            # at end of line
            last_line = this_line

        self.generate_IDs()

    def generate_IDs(self):
        for i, p in enumerate(self.pages):
            p.id = "p" + str(i + 1)
        for i, c in enumerate(self.columns):
            c.id = "c" + str(i + 1)

        # empty lines have same ID as previous line
        # (and will be ignored later on)
        for i, l in enumerate(self.lines):
            if l:
                i += 1
                l.id = "l" + str(i)
            else:
                l.id = "l" + str(i)

        # tokens require a diff. approach due to presence of comments
        i = 0
        for t in self.tokens:
            if isinstance(t, Token):
                i += 1
                t.id = "t" + str(i)
                t.generate_IDs()

    def to_xml(self):
        root = etree.Element("text")
        root.set("id", self.sigle)
        header = etree.SubElement(root, "header")
        header.text = self.headertext

        layoutinfo = etree.SubElement(root, "layoutinfo")
        for page in self.pages:
            layoutinfo.append(page.to_xml())

        for col in self.columns:
            layoutinfo.append(col.to_xml())

        for line in self.lines:
            # empty lines could come about after double dashes at 
            # line end have been resolved
            if line:
                layoutinfo.append(line.to_xml())

        shifttags = etree.SubElement(root, "shifttags")
        for shifttag in self.shifttags:
            etree.SubElement(shifttags, shifttag.tag(), {"range": shifttag.range()})

        for token_or_comment in self.tokens:
            root.append(token_or_comment.to_xml())

        return root


class Page:

    def __init__(self, pageno, side=""):
        self.no = pageno
        self.side = side
        self.columns = list()

    def range(self):
        if len(self.columns) > 1:
            first, *_, last = self.columns
            return "{0}..{1}".format(first.id, last.id)
        else:
            first = self.columns[0]
            return first.id

    def to_xml(self):
        me = etree.Element("page",{"id": self.id, 
                                   "no": self.no,
                                   "range": self.range()})
        if self.side:
            me.set("side", self.side)
        return me


class Column:
    def __init__(self, col):
        self.name = col
        self.lines = list()

    def range(self):
        if len(self.lines) > 1:
            first, *_, last = self.lines
            return "{0}..{1}".format(first.id, last.id)
        else:
            first = self.lines[0]
            return first.id

    def to_xml(self):
        me = etree.Element("column", {"id": self.id, 
                                      "range": self.range()})
        if self.name:
            me.set("name", self.name)
        return me

class Line:
    def __init__(self, linename, loc=[]):
        self.linename = linename
        self._loc = loc
        self.tokens = list()  # (will actually refer to dipls)

    def loc(self):
        return "".join(self._loc[:3]) + "," + self._loc[-1]

    def range(self):
        if len(self.tokens) > 1:
            first, *middle, last = self.tokens
            # if first dipl token was merged into last line, then it won't have an ID
            # in that case, just use second token ID for range
            if middle:
                return "{0}..{1}".format(first.id if hasattr(first, "id") else middle[0].id, 
                                         last.id)
            else:
                return "{0}..{1}".format(first.id, last.id)

        else:
            first = self.tokens[0]
            return first.id

    def __bool__(self):
        return bool(self.tokens)

    def to_xml(self):
        me = etree.Element("line", {"id": self.id,
                                    "name": self.linename,
                                    "loc": self.loc(),
                                    "range": self.range()})
        return me

class Token:
    def __init__(self, trans):
        self.trans = trans
        self.dipls = list()
        self.mods = list()

    def generate_IDs(self):
        for i, d in enumerate(self.dipls):
            d.id = "{0}_d{1}".format(self.id, i + 1)
        for i, m in enumerate(self.mods):
            m.id = "{0}_m{1}".format(self.id, i + 1)

    def merge_token(self, tok, join_dipls=False, join_mods=False):
        self.trans += tok.trans
        # if join_dipls:
            # if tok.dipls:
            #     first, *rest = tok.dipls
            #     self.dipls[-1].merge(first)
            #     self.dipls.extend(rest)
            # else:
            #     pass  # happens when token-to-merge is unintelligible
        # else:
            # self.dipls.extend(tok.dipls)

        # dipls are never merged directly in order to preserve layout info
        self.dipls.extend(tok.dipls)

        if join_mods:
            if tok.mods:
                first, *rest = tok.mods
                self.mods[-1].merge(first)
                self.mods.extend(rest)
            else:
                pass  # happens when token-to-merge is unintelligible
        else:
            self.mods.extend(tok.mods)

    def to_xml(self):
        me = etree.Element("token", {"id": self.id, 
                                     "trans": self.trans})
        for dipl in self.dipls:
            me.append(dipl.to_xml())        
        for mod in self.mods:
            me.append(mod.to_xml())
        return me

class Dipl:
    def __init__(self, trans, utf):
        self.trans = trans
        self.utf = utf

    def merge(self, dipl):
        self.trans += dipl.trans
        self.utf += dipl.utf

    def to_xml(self):
        return etree.Element("dipl", {"id": self.id,
                                      "trans": self.trans,
                                      "utf": self.utf})
        
class Mod:
    def __init__(self, trans, utf, simple):
        self.trans = trans
        self.utf = utf
        self.simple = simple

    def merge(self, mod):
        self.trans += mod.trans
        self.utf += mod.utf
        self.simple += mod.simple

    def to_xml(self):
        return etree.Element("mod", {"id": self.id,
                                     "trans": self.trans,
                                     "utf": self.utf,
                                     "ascii": self.simple})

class ShiftTag:
    def __init__(self, mytype, elements):
        self.type = mytype
        self.elements = list(elements)

    def range(self):
        if len(self.elements) > 1:
            first, *_, last = self.elements
            return "{0}..{1}".format(first.id, last.id)
        elif len(self.elements) == 1:
            first = self.elements[0]
            return first.id
        else:
            return ""

    def tag(self):
        return {"F": "fm",
                "L": "lat",
                "R": "rub",
                "Ü": "title",
                "M": "marg",
                "Q": "question"}.get(self.type, "shifttag")


class Comment:
    def __init__(self, mytype, stack):
        self.type = mytype
        self.content = " ".join(stack)

    def to_xml(self):
        me = etree.Element("comment", {"type": self.type})
        me.text = self.content
        return me


if __name__ == "__main__":
    description = "Konvertiert eine Transkriptionsdatei ins CorA-XML-Format."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('infile',
                        help='Eingabedatei (Transkription)')
    parser.add_argument('outfile', nargs="?",
                        help='Ausgabedatei (XML)')
    parser.add_argument('-t', '--tag',
                        action='store_true',
                        default=False,
                        help='Automatisches Tagging der Eingabedatei')
    parser.add_argument('-p', '--par',
                        default='/usr/local/share/rftagger/lib/bonn.par',
                        help='Parameterdatei für den RFTagger (Default: %(default)s)')
    parser.add_argument('-g', '--genus',
                        action='store_true',
                        default=False,
                        help='Genusliste für ambige Nomina benutzen')
    parser.add_argument("-P", "--parser", choices=["rem", "anselm", "ref", "redi"],
                        default="ref", help="Token parser to use, default: %(default)s")
    args, _ = parser.parse_known_args()

    if args.parser == "ref":
        from parsed_token import RefToken as ParsedToken
    elif args.parser == "rem":
        from parsed_token import RemToken as ParsedToken
    elif args.parser == "redi":
        from parsed_token import RediToken as ParsedToken
    elif args.parser == "anselm":
        from parsed_token import AnselmToken as ParsedToken

    doc = None
    with open(args.infile, "r", encoding="utf-8") as infile:
        doc = Doc(infile.read().replace("\ufeff", ""))

    if args.tag:
        pass

    if not args.outfile:
        args.outfile = doc.sigle + ".xml"

    my_xml = etree.ElementTree(doc.to_xml())
    with open(args.outfile, "wb") as outfile:
        my_xml.write(outfile, xml_declaration=True,
                     pretty_print=True, encoding='utf-8')
