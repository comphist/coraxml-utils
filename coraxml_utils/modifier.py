import json
import re
import logging
import argparse
from pathlib import Path

from coraxml_utils.settings import DEFAULT_VAL
from coraxml_utils.character import *
from coraxml_utils.coralib import ShiftTag, CoraToken

def add_tokenization_tags(token):
    c = 1
    switch_ML = False
    switch_MS = False
    for m in token.tok_annos:
        mparse = m.trans.parse

        # multiverbation
        if switch_ML:
            m.append_annotation("token_type", "ML" + str(c))
            switch_ML = False
            c += 1
        elif switch_MS:
            m.append_annotation("token_type", "MS" + str(c))
            switch_MS = False
            c += 1
        elif any(c.string == "=|" and isinstance(c, TokenBound) 
                 for c in mparse):
            switch_ML = True
            m.append_annotation("token_type", "ML1")
            c += 1
        elif any(c.string == "|" and isinstance(c, TokenBound) 
                 for c in mparse):
            switch_MS = True
            m.append_annotation("token_type", "MS1")
            c += 1

        # univerbation
        if any(isinstance(c, Hyphen) for c in mparse):
            m.append_annotation("token_type", "UH")
        elif any(c.string == "#" and isinstance(c, TokenBound) 
                 for c in mparse):
            m.append_annotation("token_type", "US")
        elif any(isinstance(c, MultiverbNewline) for c in mparse):
            m.append_annotation("token_type", "UL")

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
        if any(isinstance(c, Punct) for c in m.trans.parse):
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
def add_punc_tags(token, tagname='punc'):

    last_annotatable = None
    keep_annos = list()
    unresolved_preed_tokens = []

    for tokanno in token.tok_annos:

        if len(tokanno.trans)==1 and isinstance(tokanno.trans.parse[0], SentBound):
            if last_annotatable is not None:
                last_annotatable.append_annotation(tagname, str(tokanno.trans))
                last_annotatable.flags.add(tagname)
            else:
                unresolved_preed_tokens.append(tokanno)

        else:
            if unresolved_preed_tokens:
                for preed_tok in unresolved_preed_tokens:
                    tokanno.append_annotation(tagname, str(preed_tok.trans))
                tokanno.flags.add(tagname)
                unresolved_preed_tokens = []
                tokanno.append_annotation(tagname, '|')

            last_annotatable = tokanno
            keep_annos.append(tokanno)

    token.trans = token.trans.delete(SentBound)
    for dipl in token.tok_dipls:
        dipl.trans = dipl.trans.delete(SentBound)
        ### TODO make sure dipl.trans is not empty
    token.tok_annos = keep_annos

def merge_annotations(token, source_anno1_name, source_anno2_name, res_anno_name, sep='.'):

    for tok_anno in token.tok_annos:

        if source_anno1_name in tok_anno.tags:
            if source_anno2_name in tok_anno.tags:
                ## both source annos
                ## 1. create new tag
                combined_tag = tok_anno.tags[source_anno1_name] + sep + tok_anno.tags[source_anno2_name]
                ## 2. remove old annotations
                del tok_anno.tags[source_anno1_name]
                del tok_anno.tags[source_anno2_name]
            else:
                ## only source anno1
                ## keep this tag under new name
                combined_tag = tok_anno.tags[source_anno1_name]
                del tok_anno.tags[source_anno1_name]
            ## add new annotation
            tok_anno.tags[res_anno_name] = combined_tag

        ### TODO just for readability?
        else:
            ## if source_anno1_name does not exist -> do nothing
            pass

def trans_to_cora_json(trans):
    """
    Converts a Trans-object to json as expected from CorA from a token editing script
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

### project specific postprocessing

def postprocess(MyImporter, MyExporter, postprocessor, document_processor=None):

    description = "Fügt einige extra Annotationen einer CorA-XML-Datei hinzu."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('infiles', nargs="+", help='Eingabedateien (XML)')
    parser.add_argument("-o", '--outpath', default=".",
                        help='Ausgabepfad')
    args, _ = parser.parse_known_args()

    # name mod -> tok_anno, dipl -> tok_dipl

    for filepath in args.infiles:

        print("processing %s..." % filepath)
        doc = MyImporter.import_from_file(filepath)

        if doc is None:
            print("Error: Could not load document %s" %filepath)
            continue

        for tok in filter(lambda x: isinstance(x, CoraToken), doc.tokens):

            postprocessor(tok)

        if document_processor:
            document_processor(doc)

        output_xml = MyExporter.export(doc)
        outfilepath = str(Path(args.outpath) / (doc.sigle + ".xml"))
        with open(outfilepath, "wb") as outfile:
            output_xml.write(outfile, xml_declaration=True,
                             pretty_print=True, encoding='utf-8')

def ref_postprocess(tok):

    # add tokenization tags
    add_tokenization_tags(tok)

    # add punc tags
    add_punc_tags(tok)

def anselm_postprocess(tok, doc):

    for tok_anno in tok.tok_annos:
        # remove comment and boundary
        tok_anno.tags.pop('comment', None)
        tok_anno.tags.pop('boundary', None)
        tok_anno.flags.discard('boundary')

        # add "--" if morph is not set
        fill_annotation_column(tok_anno, 'morph')

        # add norm if it is missing
        if 'norm' not in tok_anno.tags:
            print(tok_anno)
        # set norm_broad to norm if it is not set
        if 'norm' in tok_anno.tags:
            fill_annotation_column(tok_anno, 'norm_broad', tok_anno.tags['norm'])

        # rename norm_type-tags
        change_tags(tok_anno, 'norm_type', {
            'f': 'inflection',
            's': 'semantic',
            'x': 'extinct'
        })

    # add tokenization tags
    add_tokenization_tags(tok)

    # add punc tags
    # ANSELM: as yet no pre-edition punctuation 
    # (and therefore no sent bounds discernible)
    # tok = add_punc_tags(tok)

    # alle Satzzeichen (type = p) auf $( setzen (wenn noch nichts gesetzt)
    update_punct_pos(tok)


