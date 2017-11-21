


# nach coraxml
class Doc:


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



    def to_xml(self):
        me = etree.Element("page",{"id": self.id, 
                                   "no": self.no,
                                   "range": self.range()})
        if self.side:
            me.set("side", self.side)
        return me


class Column:


    def to_xml(self):
        me = etree.Element("column", {"id": self.id, 
                                      "range": self.range()})
        if self.name:
            me.set("name", self.name)
        return me

class Line:


    def to_xml(self):
        me = etree.Element("line", {"id": self.id,
                                    "name": self.linename,
                                    "loc": self.loc(),
                                    "range": self.range()})
        return me

class Token:


    def to_xml(self):
        me = etree.Element("token", {"id": self.id, 
                                     "trans": self.trans})
        for dipl in self.dipls:
            me.append(dipl.to_xml())        
        for mod in self.mods:
            me.append(mod.to_xml())
        return me

class Dipl:


    def to_xml(self):
        return etree.Element("dipl", {"id": self.id,
                                      "trans": self.trans,
                                      "utf": self.utf})
        
class Mod:


    def to_xml(self):
        return etree.Element("mod", {"id": self.id,
                                     "trans": self.trans,
                                     "utf": self.utf,
                                     "ascii": self.simple})



class Comment:


    def to_xml(self):
        me = etree.Element("comment", {"type": self.type})
        me.text = self.content
        return me
