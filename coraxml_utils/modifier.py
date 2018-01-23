
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