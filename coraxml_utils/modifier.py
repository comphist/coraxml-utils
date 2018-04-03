import json
import re
import logging

from coraxml_utils.settings import DEFAULT_VAL
from coraxml_utils.character import *
from coraxml_utils.coralib import ShiftTag

def _add_val(instr, newval, sep=' '):
    if instr != DEFAULT_VAL:
        return (instr + sep + newval).strip()
    else:
        return newval


def add_tokenization_tags(token):
    c = 1
    switch_ML = False
    switch_MS = False
    for m in token.tok_annos:
        token_type = m.tags.get("token_type", DEFAULT_VAL)
        mparse = m.trans.parse

        # multiverbation
        if switch_ML:
            token_type = _add_val(token_type, "ML" + str(c))
            switch_ML = False
            c += 1
        elif switch_MS:
            token_type = _add_val(token_type, "MS" + str(c))
            switch_MS = False
            c += 1
        elif any(c.string == "=|" and isinstance(c, TokenBound) 
                 for c in mparse):
            switch_ML = True
            token_type = _add_val(token_type, "ML1")
            c += 1
        elif any(c.string == "|" and isinstance(c, TokenBound) 
                 for c in mparse):
            switch_MS = True
            token_type = _add_val(token_type, "MS1")
            c += 1

        # univerbation
        if any(isinstance(c, Hyphen) for c in mparse):
            token_type = _add_val(token_type, 'UH')
        elif any(c.string == "#" and isinstance(c, TokenBound) 
                 for c in mparse):
            token_type = _add_val(token_type, 'US')
        elif any(isinstance(c, EditHyphen) for c in mparse):
            token_type = _add_val(token_type, 'UL')

        if token_type and token_type != DEFAULT_VAL:
            m.tags["token_type"] = token_type


# def add_punc_tags(token):
#     mods = token.tok_annos
    
#     for i, m in enumerate(mods):
#         sent_type = str()
#         nom_type = str()
#         mtrans = str(m.trans)
        
#         if mtrans == "(.)":
#             sent_type = "DE"
#         elif mtrans == "(?)":
#             sent_type = "QE"
#         elif mtrans == "(!)":
#             sent_type = "EE"
#         elif mtrans == "(;)": # semicolon end
#             sent_type = "SE"
#         elif mtrans == "(:)": # colon end
#             sent_type = "CE"

#         if mtrans == "(,)":
#             nom_type = "C" # modern comma

#         if sent_type:
#             # TODO: adapt to cases w/multiple punct
#             if mods[i - 1].trans.keep("p") and len(mods) > 2:
#                 etree.SubElement(mods[i - 2], "punc", {"tag": sent_type})
#                 etree.SubElement(mods[i - 1], "punc", {"tag": "$E"})
#             else:
#                 etree.SubElement(mods[i - 1], "punc", {"tag": sent_type})
#             token.remove(m)

#         if nom_type:
#             if mods[i - 1].trans.keep("p") and len(mods) > 2:
#                 etree.SubElement(mods[i - 2], "punc", {"tag": nom_type})
#                 etree.SubElement(mods[i - 1], "punc", {"tag": "$C"})
#             else:
#                 etree.SubElement(mods[i - 1], "punc", {"tag": nom_type})
#             try:
#                 token.remove(m)
#             except ValueError:
#                 print(token.id)


def update_punct_pos(token):
    for m in token.tok_annos:
        if any(c["type"] == "p" for c in m.trans.parse):
            if m.tags.get("pos", DEFAULT_VAL) == DEFAULT_VAL:
                m.tags["pos"] = "$("

def fill_annotation_column(tok_anno, annotation_type, default_value=DEFAULT_VAL):
    """Add a default value if the token is not annotated with an annotation of the given type."""
    tok_anno.tags[annotation_type] = tok_anno.tags.get(annotation_type, default_value)

def change_tags(tok_anno, annotation_type, rename_dict):
    """Change certain tags of the given type to a new value that is specified in rename_dict."""
    if annotation_type in tok_anno.tags:
        tok_anno.tags[annotation_type] = rename_dict.get(tok_anno.tags[annotation_type], 
                                                         tok_anno.tags[annotation_type])


# für REF
def add_punc_tags(token):
    last_anno = None
    keep_annos = list()
    open_quote = False
    new_shifttags = list()
    shifttag_stack = list()
    for tokanno in token.tok_annos:
        anno_string = str(tokanno.trans)
        if re.match(r"\([.;!?:,]\)", anno_string):
            keep_annos[-1].tags["punc"] = tokanno.trans.parse[0].string.replace("(", "").replace(")", "")

            # remove PE chars from utf & simple representations
            for c in tokanno.trans.parse:
                c.dipl_utf = ""
                c.anno_utf = ""
                c.anno_simple = ""
            keep_annos[-1].trans += tokanno.trans

        elif anno_string == '(")':
            if last_anno:
                if re.match(r"\([.;!?:,]\)", str(last_anno.trans)):
                    # set this token as end of span
                    new_shifttags.append(ShiftTag("Q", shifttag_stack))
                    shifttag_stack = list()
                else:
                    logging.warning("Unexpected quotation mark in token: " + str(token))
            else:
                # set this token as beginning of span
                open_quote = True
        else:
            if open_quote:
                shifttag_stack.append(token)
            keep_annos.append(tokanno)
    token.tok_annos = keep_annos
    return new_shifttags


def trans_to_cora_json(trans):
    """converts a Trans-object to json as expected from CorA from a token editing script
    https://cora.readthedocs.io/en/latest/admin-projects/#setting-a-token-editing-script
    """

    json_dict = {
        'dipl_trans': [''],
        'dipl_utf': [''],
        'dipl_breaks': [],
        'mod_trans': [''],
        'mod_utf': [''],
        'mod_ascii': [''],
    }

    for char in trans.parse:

        if char.dipl_bound:
            json_dict['dipl_trans'].append('')
            json_dict['dipl_utf'].append('')
            if char.line_break:
                json_dict['dipl_breaks'].append(1)
            else:
                json_dict['dipl_breaks'].append(0)

        if char.anno_bound:
            json_dict['mod_trans'].append('')
            json_dict['mod_utf'].append('')
            json_dict['mod_ascii'].append('')

        if not isinstance(char, Whitespace):
            json_dict['dipl_trans'][-1] += char.string
            json_dict['dipl_utf'][-1] += char.dipl_utf
            json_dict['mod_trans'][-1] += char.string
            json_dict['mod_utf'][-1] += char.anno_utf
            json_dict['mod_ascii'][-1] += char.anno_simple

    json_dict['dipl_breaks'].append(0)

    return json.dumps(json_dict)
