
from coraxml_utils.settings import DEFAULT_VAL

def add_val(instr, newval, sep=' '):
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
            token_type = add_val(token_type, f"ML{c}")
            switch_ML = False
            c += 1
        elif switch_MS:
            token_type = add_val(token_type, f"MS{c}")
            switch_MS = False
            c += 1
        elif any(c["trans"] == "=|" and c["type"] == "spl" 
                 for c in mparse):
            switch_ML = True
            token_type = add_val(token_type, "ML1")
            c += 1
        elif any(c["trans"] == "|" and c["type"] == "spl" 
                 for c in mparse):
            switch_MS = True
            token_type = add_val(token_type, "MS1")
            c += 1

        # univerbation
        if any(c["type"] == "dd" for c in mparse):
            token_type = add_val(token_type, 'UH')
        elif any(c["trans"] == "#" and c["type"] == "spl" 
                 for c in mparse):
            token_type = add_val(token_type, 'US')
        elif any(c["trans"] == "~(=)" and c["type"] == "spl" 
                 for c in mparse):
            pass
        elif any(c["trans"] == "(=)" and c["type"] == "spl" 
                 for c in mparse):
            token_type = add_val(token_type, 'UL')

        if token_type and token_type != DEFAULT_VAL:
            m.tags["token_type"] = token_type
    return token


def add_punc_tags(token):
    mods = token.tok_annos
    
    for i, m in enumerate(mods):
        sent_type = str()
        nom_type = str()
        mtrans = str(m.trans)
        
        if mtrans == "(.)":
            sent_type = "DE"
        elif mtrans == "(?)":
            sent_type = "QE"
        elif mtrans == "(!)":
            sent_type = "EE"
        elif mtrans == "(;)": # semicolon end
            sent_type = "SE"
        elif mtrans == "(:)": # colon end
            sent_type = "CE"

        if mtrans == "(,)":
            nom_type = "C" # modern comma

        if sent_type:
            # TODO: adapt to cases w/multiple punct
            if mods[i - 1].trans.keep("p") and len(mods) > 2:
                etree.SubElement(mods[i - 2], "punc", {"tag": sent_type})
                etree.SubElement(mods[i - 1], "punc", {"tag": "$E"})
            else:
                etree.SubElement(mods[i - 1], "punc", {"tag": sent_type})
            token.remove(m)

        if nom_type:
            if mods[i - 1].trans.keep("p") and len(mods) > 2:
                etree.SubElement(mods[i - 2], "punc", {"tag": nom_type})
                etree.SubElement(mods[i - 1], "punc", {"tag": "$C"})
            else:
                etree.SubElement(mods[i - 1], "punc", {"tag": nom_type})
            try:
                token.remove(m)
            except ValueError:
                print(token.id)
            
    return token


def update_punct_pos(token):
    for m in token.tok_annos:
        if any(c["type"] == "p" for c in m.trans.parse):
            if m.tags.get("pos", DEFAULT_VAL) == DEFAULT_VAL:
                m.tags["pos"] = "$("
    return token

## adds a default value if the token is not annotated with an annotation of the given type
def fill_annotation_column(tok_anno, annotation_type, default_value="--"):
    tok_anno.tags[annotation_type] = tok_anno.tags.get(annotation_type, default_value)

## change tags to a new value, specified with a dict
def change_tags(tok_anno, annotation_type, rename_dict):
    if annotation_type in tok_anno.tags:
        tok_anno.tags[annotation_type] = rename_dict.get(tok_anno.tags[annotation_type], tok_anno.tags[annotation_type])
