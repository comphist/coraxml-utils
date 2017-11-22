
from coraxml_utils.settings import *



### TODO: diese sachen sollen in den jeweiligen tokenparser
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


##################################
### TODOs:

class CoraTag:
    pass

class CoraFlag:
    pass


#################################



class Document:

    def __init__(self, sigle, name, header, pages, tokens, shifttags):
        self.sigle = sigle
        self.name = name
        self.header = header

        self.pages = pages
        self.tokens = tokens
        self.shifttags = shifttags

    def __bool__(self):
        return bool(self.pages and self.tokens)


class Page:

    def __init__(self, name, side, columns):
        self.name = name
        self.side = side
        self.columns = columns

    def range(self):
        if len(self.columns) > 1:
            first, *_, last = self.columns
            return "{0}..{1}".format(first.id, last.id)
        else:
            first = self.columns[0]
            return first.id

    def __bool__(self):
        return bool(self.columns)


class Column:
    def __init__(self, name, lines):
        self.name = name
        self.lines = lines

    def range(self):
        if len(self.lines) > 1:
            first, *_, last = self.lines
            return "{0}..{1}".format(first.id, last.id)
        else:
            first = self.lines[0]
            return first.id

    def __bool__(self):
        return bool(self.lines)


class Line:
    def __init__(self, name, dipls):
        self.name = name
        self.dipls = dipls

    def __bool__(self):
        return bool(self.dipls)

    ## keep?
    def loc(self):
        pass

    def range(self):
        if len(self.dipls) > 1:
            first, *middle, last = self.dipls
            # if first dipl token was merged into last line, then it won't have an ID
            # in that case, just use second token ID for range
            if middle:
                return "{0}..{1}".format(first.id if hasattr(first, "id") else middle[0].id, 
                                         last.id)
            else:
                return "{0}..{1}".format(first.id, last.id)

        else:
            first = self.dipls[0]
            return first.id


class CoraToken:

    def __init__(self, _id, trans, tok_dipls, tok_annos):
        self.id = _id
        self.trans = trans
        self.tok_dipls = tok_dipls
        self.tok_annos = tok_annos

    def __str__(self):
        return str(self.trans)

    def merge_token(self, tok, join_dipls=False, join_mods=False):
        self.trans += tok.trans

        # dipls are never merged directly in order to preserve layout info
        self.tok_dipls.extend(tok.tok_dipls)

        if join_mods:
            if tok.tok_annos:
                first, *rest = tok.tok_annos
                self.tok_annos[-1].merge(first)
                self.tok_annos.extend(rest)
            else:
                pass  # happens when token-to-merge is unintelligible
        else:
            self.tok_annos.extend(tok.tok_annos)


class TokDipl:

    def __init__(self, _id, trans):
        self.id = _id
        self.trans = trans

    def __str__(self):
        return str(self.trans)

    def merge(self, dipl):
        self.trans += dipl.trans
        self.utf += dipl.utf

    def __eq__(self, other):
        return (self.id == other.id) and (self.trans == other.trans)

class CoraComment:

    def __init__(self, _type, content):
        self.type = _type
        self.content = content

    def __str__(self):
        return "+{0} {1} @{0}".format(self.type, 
                                      " ".join(self.content))


class ShiftTag:

    def __init__(self, _type, tokens):
        self.type = _type
        self.tokens = tokens

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











class Mod:
    def __init__(self, trans, utf, simple):
        self.trans = trans
        self.utf = utf
        self.simple = simple

    def merge(self, mod):
        self.trans += mod.trans
        self.utf += mod.utf
        self.simple += mod.simple




class CoraMod:

    annos_order = ["norm", "token_type", "lemma", "lemma_gen", "lemma_idmwb", "pos",
                   "pos_gen", "infl", "inflClass", "inflClass_gen", "punc", "link"]

    def __init__(self, id='', trans='', utf='', ascii='',
                 mod_elem=None):
        self.annotations = dict()
        self.annotations["targets"] = dict()
        if mod_elem is not None:
            self.id = mod_elem.attrib['id']
            self.ascii = remove_majuskel(
                           unspace(mod_elem.attrib['ascii']))
            self.trans = mod_elem.attrib['trans']
            self.utf = remove_majuskel(
                         normalize('NFC', unspace(mod_elem.attrib['utf'])))
            for subelem in mod_elem:
                key = subelem.tag
                val = subelem.get("tag")

                # special case for VPC links
                if val is None:
                    val = subelem.get("target")

                try:
                    # standardize empty values
                    if not re.match(r"[\s-]*$", val):
                        self.annotations[key] = val
                    else:
                        self.annotations[key] = DEFAULT_VAL
                except TypeError:
                    pass
        else:
            self.id = id
            self.trans = trans
            self.utf = utf
            self.ascii = ascii

    def __str__(self):
        return ET.tostring(self.to_xml(), pretty_print=True, encoding='utf-8').decode()


