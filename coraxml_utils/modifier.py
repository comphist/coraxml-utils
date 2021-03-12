import json
import csv
import re
import logging
import argparse
from pathlib import Path

from coraxml_utils.settings import DEFAULT_VAL
from coraxml_utils.character import *
from coraxml_utils.coralib import ShiftTag, CoraToken, TokDipl


def add_tokenization_tags(token):
    c = 1
    switch_ML = False
    switch_MS = False
    for m in token.tok_annos:
        # multiverbation
        if switch_ML:
            m.append_annotation("token_type", "ML" + str(c))
            switch_ML = False
            c += 1
        elif switch_MS:
            m.append_annotation("token_type", "MS" + str(c))
            switch_MS = False
            c += 1
        elif m.trans.has(MultiverbNewline):
            switch_ML = True
            m.append_annotation("token_type", "ML1")
            c += 1
        elif m.trans.has(MultiverbSpace):
            switch_MS = True
            m.append_annotation("token_type", "MS1")
            c += 1

        # univerbation
        # (allow multiple)
        for zeichen in m.trans.parse:
            if isinstance(zeichen, Hyphen):
                m.append_annotation("token_type", "UH")
            if isinstance(zeichen, UniverbSpace):
                m.append_annotation("token_type", "US")
            if isinstance(zeichen, UniverbNewline):
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


def remove_annotation_column(tok_anno, annotation_type, value=DEFAULT_VAL):
    """Remove an annotation column if it is annotated with a given value,
       e.g. before uploading the text to CorA."""
    if tok_anno.tags[annotation_type] == value:
        del tok_anno.tags[annotation_type]


def change_tags(tok_anno, annotation_type, rename_dict):
    """Change certain tags of the given type to a new value that is specified in rename_dict."""
    if annotation_type in tok_anno.tags:
        tok_anno.tags[annotation_type] = rename_dict.get(
            tok_anno.tags[annotation_type], tok_anno.tags[annotation_type]
        )


# für REF
def add_punc_tags(token, tagname="punc"):

    last_annotatable = None
    keep_annos = list()
    unresolved_preed_tokens = []

    for tokanno in token.tok_annos:

        if len(tokanno.trans) == 1 and isinstance(tokanno.trans.parse[0], SentBound):
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
                tokanno.append_annotation(tagname, "|")

            last_annotatable = tokanno
            keep_annos.append(tokanno)

    token.trans = token.trans.delete(SentBound)
    for dipl in token.tok_dipls:
        dipl.trans = dipl.trans.delete(SentBound)
        ### TODO make sure dipl.trans is not empty
    token.tok_annos = keep_annos


def merge_annotations(
    token, source_anno1_name, source_anno2_name, res_anno_name, sep="."
):

    for tok_anno in token.tok_annos:

        if source_anno1_name in tok_anno.tags:
            if source_anno2_name in tok_anno.tags:
                ## both source annos
                ## 1. create new tag
                combined_tag = (
                    tok_anno.tags[source_anno1_name]
                    + sep
                    + tok_anno.tags[source_anno2_name]
                )
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

def split_annotations(token, source_anno_name, res_anno1_name, res_anno2_name, sep='.'):

    for tok_anno in token.tok_annos:
        if source_anno_name in tok_anno.tags:
            annos = [a.strip() for a in tok_anno.tags[source_anno_name].split(sep) if a.strip()]
            if len(annos) > 1:
                ## both res annos
                ## create new annotations
                tok_anno.tags[res_anno1_name] = annos[0]
                tok_anno.tags[res_anno2_name] = annos[1]
            else:
                ## only res anno1
                ## keep this tag under new name
                tok_anno.tags[res_anno1_name] = tok_anno.tags[source_anno_name]

            #Remove source tag
            if source_anno_name != res_anno1_name and source_anno_name != res_anno1_name:
                del tok_anno.tags[source_anno_name]
                    
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
        "dipl_trans": [""],
        "dipl_utf": [""],
        "dipl_breaks": [],
        "mod_trans": [""],
        "mod_utf": [""],
        "mod_ascii": [""],
    }

    for char in trans.parse:

        if char.dipl_bound:
            json_dict["dipl_trans"].append("")
            json_dict["dipl_utf"].append("")
            if isinstance(char, LineBreak):
                json_dict["dipl_breaks"].append(1)
            elif char.line_break_after:
                json_dict["dipl_breaks"].append(1)
            else:
                json_dict["dipl_breaks"].append(0)

        if char.anno_bound:
            json_dict["mod_trans"].append("")
            json_dict["mod_utf"].append("")
            json_dict["mod_ascii"].append("")

        if not isinstance(char, Whitespace):
            json_dict["dipl_trans"][-1] += char.string
            json_dict["dipl_utf"][-1] += char.dipl_utf
            json_dict["mod_trans"][-1] += char.string
            json_dict["mod_utf"][-1] += char.anno_utf
            json_dict["mod_ascii"][-1] += char.anno_simple

    json_dict["dipl_breaks"].append(0)

    return json.dumps(json_dict)


### project specific postprocessing


def postprocess(MyImporter, MyExporter, postprocessor, document_processor=None):

    description = "Fügt einige extra Annotationen einer CorA-XML-Datei hinzu."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("infiles", nargs="+", help="Eingabedateien (XML)")
    parser.add_argument("-o", "--outpath", default=".", help="Ausgabepfad")
    args, _ = parser.parse_known_args()

    # name mod -> tok_anno, dipl -> tok_dipl

    for filepath in args.infiles:

        print("processing %s..." % filepath)
        doc = MyImporter.import_from_file(filepath)

        if doc is None:
            print("Error: Could not load document %s" % filepath)
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

def ref_convert(tok):

    merge_annotations(tok, 'pos', 'lemmapos', 'pos', sep='<')
    merge_annotations(tok, 'pos', 'morph', 'pos', sep='.')

    # add punc tags
    add_punc_tags(tok, 'boundary')

def ref_header(doc):

    new_header_string = []

    # delete unnecessary info from header
    lines_to_delete = ["Text eingegeben", "Datum", "Bearbeiter",
                       "Text präeditiert", 
                       "Text kollationiert",
                       "Lat. Passage",
                       "Annotiert", 
                       "KTX-Korrektur"]
    mapping = [("Korpus-Sigle", "corpus-sigle"),
               ("Titel", "text"),
               ("Verfasser", "text-author"),
               #("Textart", "genre"),
               ("Text[\$s]orte", "text-type"),
               ("Zuordnung[$s]qualität", "assignment_quality"),
               ("Hoffmann/Wetter-Nr", "hoffmann_wetter_nr"),
               ("Bibliothek/Archiv", "library"),
               ("[$S]ignatur", "library-shelfmark"),
               ("Datierung", "date"),
               #("Lokali[$s]ierung", "text-place"),
               ("Druckort", "place"),
               ("Schreibort", "text-place"),
               ("Drucker", "printer"),
               ("verwendete\sEdition", "edition"),
               ("Literatur", "literature"),
               ("(Ge[$s]amtumfang|Umfang\s*in\s*Wortformen\s*:|Umfang\s*in\s*Wortformen\s*\(*\s*insgesamt\s*\)*)", "size")]

    header = [line.strip() for line in doc.header_string.strip().split("\n") if line.strip()]

    new_header_dict = dict()
    
    for oldkey,newkey in mapping:
        for line in header:
            if re.match(oldkey, line, re.I):
                val = ":".join(line.split(":")[1:]).strip()
                if not val: val = "-"
                elif re.match(r"^-+$", val): val = "-"
                new_header_dict[newkey] = val
    for _, newkey in mapping:
        if newkey in new_header_dict:
            if newkey == "corpus-sigle":
                match = re.search(r"(F\d+)[,\s]*([IV]+)-([A-F])([a-f]+)-([PVT])\d*[,(\s]*(H|D)", new_header_dict[newkey])
                new_header_dict["time"] = {"I" : "14,2", "II" : "15,1", "III" : "15,2",
                                           "IV" : "16,1", "V" : "16,2", "VI" : "17,1"}.get(match.group(2), "-")
                if match.group(3) == "B":
                    new_header_dict["language-type"] = "oberdeutsch"
                    new_header_dict["language-region"] = "westoberdeutsch"
                    if match.group(4) == "a":
                        new_header_dict["language-area"] = "oberrheinisch"
                    elif match.group(4) == "b":
                        new_header_dict["language-area"] = "hochalemannisch"
                    elif match.group(4) == "c":
                        new_header_dict["language-area"] = "schwäbisch"
                    elif match.group(4) == "d":
                        new_header_dict["language-area"] = "ostschwäbisch"
                    elif match.group(4) == "cd":
                        new_header_dict["language-area"] = "gesamtschwäbisch"
                elif match.group(3) == "C":
                    new_header_dict["language-type"] = "mitteldeutsch"
                    new_header_dict["language-region"] = "westmitteldeutsch"
                    if match.group(4) == "a":
                        new_header_dict["language-area"] = "ripuarisch"
                    elif match.group(4) == "b":
                        new_header_dict["language-area"] = "moselfränkisch"
                    elif match.group(4) == "c":
                        new_header_dict["language-area"] = "hessisch"
                    elif match.group(4) == "d":
                        new_header_dict["language-area"] = "südrheinfränkisch"
                    elif match.group(4) == "cd":
                        new_header_dict["language-area"] = "hessisch-südrheinfränkisch"
                    elif match.group(4) == "abcd":
                        new_header_dict["language-area"] = "westmitteldeutsch"
                else:
                    new_header_dict["language-area"] = "-"
                    new_header_dict["language-region"] = "-"
                    new_header_dict["language-type"] = "-"
                new_header_dict["genre"] = match.group(5)
                if match.group(6) == "H":
                    new_header_dict["medium"] = "Handschrift"
                    new_header_dict["reference"] = "Hs.: Blatt (r/v), Kolumne (a/b), Zeile"
                else:
                    new_header_dict["medium"] = "Druck"
                    new_header_dict["reference"] = "Seite, Zeile"

                for key in ["language-area", "language-region", "language-type", "genre", "medium", "time", "reference"]:
                    new_header_string.append(key + ": " + new_header_dict[key])
            elif newkey in ["text-place", "place"]:
                if new_header_dict["medium"] == "Handschrift" and newkey == "place":
                    new_header_dict["text-place"] = new_header_dict[newkey]
                    new_header_string.append(newkey + ": -")
                    newkey = "text-place"
                elif new_header_dict["medium"] == "Handschrift" and "place" in new_header_dict:
                    continue
            new_header_string.append(newkey + ": " + new_header_dict[newkey])
        else:
            new_header_string.append(newkey + ": -")
    new_header_string.append("language: fnhd")
    new_header_string.append("corpus: ReF.BO")
***REMOVED***

    notes = {l.split("\t")[0] : l.split("\t")[1].strip() for l in notesfile.readlines() if l.strip()}
    notesfile.close()
    new_header_string.append("notes-transcription" + ": " + notes[new_header_dict["corpus-sigle"][:4]])

***REMOVED***
    abbrs = {l.split("\t")[1].strip() : l.split("\t")[0].strip() for l in abbr_file.readlines() if l.strip()}
    abbr_file.close()
    new_header_string.append("abbr_ddd" + ": " + abbrs[new_header_dict["corpus-sigle"][:4]])
    
    extent_fnhdc = ""
    extent_ref = ""
    size_fnhdc = ""
    size_ref = ""
    for line in header:
        if re.match(r"Auswahl\s*Bonner\s*Frnhd\.\s*Korpus", line, re.I):
            extent_fnhdc = ":".join(line.split(":")[1:]).strip()
        elif re.match(r"Auswahl\s*Referenzkorpus", line, re.I) \
             or re.match(r"Ergänzung\s*Referenzkorpus", line, re.I):
            if extent_ref: extent_ref += ", " + ":".join(line.split(":")[1:]).strip()
            else: extent_ref += ":".join(line.split(":")[1:]).strip()
        elif re.match(r"Umfang\s*in\s*Wortformen\s*\(\s*Frnhd\.\s*Korpus\s*\)", line, re.I):
            size_fnhdc = ":".join(line.split(":")[1:]).strip()
        elif re.match(r"Umfang\s*in\s*Wortformen\s*\(\s*Referenzkorpus\s*\)", line, re.I):
            size_ref = ":".join(line.split(":")[1:]).strip()
    if not extent_fnhdc: extent_fnhdc = "-"
    elif re.match(r"^-+$", extent_fnhdc): extent_fnhdc = "-"
    if not extent_ref: extent_ref = "-"
    elif re.match(r"^-+$", extent_ref): extent_ref = "-"
    new_header_string.append("extent: FnhdC: " + extent_fnhdc + "; compl: " + extent_ref)

    if not size_fnhdc: size_fnhdc = "-"
    elif re.match(r"^-+$", size_fnhdc): size_fnhdc = "-"
    if not size_ref: size_ref = "-"
    elif re.match(r"^-+$", size_ref): size_ref = "-"
    size = "FnhdC: " + str(size_fnhdc) + "; compl: " + str(size_ref)
    new_header_string.append("extent-size: " + str(size))
    
    doc.header_string = "\n".join(new_header_string)

def ref_postprocess(tok, link_style=False):

    #re-separate annotations
    split_annotations(tok, "pos", "pos", "posLemma", sep="<")
    split_annotations(tok, "lemma", "lemma", "lemmaId", sep=" ")

    #Create lemma URL or link
    for tok_anno in tok.tok_annos:
        if "lemmaId" in tok_anno.tags:
            lemmaId = re.search(r".*?\[{0,1}(?P<lemmaId>\w+)\]{0,1}.*?", tok_anno.tags["lemmaId"]).group("lemmaId")
            if link_style:
                tok_anno.tags["lemmaURL"] = "<a href=\'http://www.woerterbuchnetz.de/DWB?lemid={0}\'>{1}</a>".format(lemmaId, lemmaId)
            else:
                tok_anno.tags["lemmaURL"] = "http://www.woerterbuchnetz.de/DWB?lemid={0}".format(lemmaId)
        elif "lemma" in tok_anno.tags:
            lemma = tok_anno.tags["lemma"].strip()
            if link_style:
                tok_anno.tags["lemmaURL"] = "<a href=\'http://www.woerterbuchnetz.de/DWB?lemma={0}\'>{1}</a>".format(lemma, lemma)
            else:
                tok_anno.tags["lemmaURL"] = "http://www.woerterbuchnetz.de/DWB?lemma={0}".format(lemma)

        #Correct inflection of irregular verbs
        #VV: gönnen, taugen, turren, wissen, gehen, stehen, tun, lassen
        #VA: haben, sein
        #VM: dürfen, können, mögen, müssen, sollen, wollen
        #final * -> Unr
        if "pos" in tok_anno.tags and tok_anno.tags["pos"].startswith("V") \
           and "lemma" in tok_anno.tags and "morph" in tok_anno.tags \
           and len(tok_anno.tags["morph"].split(".")) == 5 \
           and tok_anno.tags["morph"].endswith("*"):
            if (tok_anno.tags["pos"].startswith("VV") \
               and tok_anno.tags["lemma"] in ["gönnen", "taugen", "turren", "wissen", \
                                              "gehen", "stehen", "tun", "lassen"]) \
               or (tok_anno.tags["pos"].startswith("VA") \
               and tok_anno.tags["lemma"] in ["haben", "sein"]) \
               or (tok_anno.tags["pos"].startswith("VM") \
               and tok_anno.tags["lemma"] in ["dürfen", "können", "mögen", "müssen", \
                                              "sollen", "wollen"]):
                inflection = tok_anno.tags["morph"].split(".")
                inflection[-1] = "Unr"
                tok_anno.tags["morph"] = ".".join(inflection)
                
        #mark automatic vs. manual annotation
        if tok_anno.checked == True:
            tok_anno.tags["annoType"] = "man"
        else:
            tok_anno.tags["annoType"] = "auto"

    # add tokenization tags
    add_tokenization_tags(tok)

    # add punc tags
    add_punc_tags(tok)


def anselm_correct_tokenization(doc):

    marginalia = set()
    for st in doc.shifttags:
        if st.tag() == "marg":
            for t in st.tokens:
                marginalia.add(t.id)

    for tok in filter(lambda x: isinstance(x, CoraToken), doc.tokens):

        if "err_nr_dipl" in tok.errors or "err_tok_dipl" in tok.errors:

            old_dipls = set()
            # relevant lines in order
            all_rel_lines = []
            for old_dipl in tok.tok_dipls:
                old_dipls.add(old_dipl.id)
                my_line = doc.get_line_for_dipl(old_dipl)
                if my_line not in all_rel_lines:
                    all_rel_lines.append(my_line)

            current_index = all_rel_lines[0].dipls.index(tok.tok_dipls[0])

            # remove old dipls from layout
            for line in all_rel_lines:
                line.dipls = list(filter(lambda x: x.id not in old_dipls, line.dipls))

            # generate new dipls
            tok.tok_dipls = list()
            legacy_counter = 1
            new_dipls = tok.trans.tokenize_dipl()
            for new_dipl_trans in new_dipls:
                new_dipl = TokDipl(
                    new_dipl_trans, "{0}_d{1}".format(tok.id, legacy_counter)
                )
                tok.tok_dipls.append(new_dipl)
                legacy_counter += 1

            # add new dipls to lines
            line_bound = False
            for new_dipl in tok.tok_dipls:
                if line_bound:

                    # don't start new line if in middle of line
                    if current_index < len(all_rel_lines[0].dipls):
                        pass
                    else:
                        if len(all_rel_lines) == 1:
                            # find next line
                            last_id = None
                            for page in doc.pages:
                                for col in page.columns:
                                    for line in col.lines:
                                        if last_id == all_rel_lines[0].id:
                                            all_rel_lines.append(line)
                                            break
                                        last_id = line.id
                        # start new line
                        current_index = 0
                        all_rel_lines.pop(0)

                    all_rel_lines[0].dipls.insert(current_index, new_dipl)
                    doc._create_indices()

                    # dipl has own line: don't set line_bound
                    #  otherwise line continues, remove line_bound flag:
                    if not new_dipl.trans.has(Joiner):
                        line_bound = False

                else:
                    # add dipl normally
                    all_rel_lines[0].dipls.insert(current_index, new_dipl)
                    doc._create_indices()
                    current_index += 1

                    if new_dipl.trans.has(Joiner) and tok.id not in marginalia:
                        logging.warn("correcting at line bound: %s (prob ok)" % tok.id)
                        line_bound = True

        if "err_tok_anno" in tok.errors:
            ###    new trans
            for old_anno_tok, new_anno_trans in zip(
                tok.tok_annos, tok.trans.tokenize_anno()
            ):
                if new_anno_trans.has(Majuscule):
                    old_anno_tok.trans = new_anno_trans
                else:
                    logging.info(
                        "did not correct error of "
                        + "type 'err_tok_anno': '{0}' -> '{1}'".format(
                            old_anno_tok.trans, new_anno_trans
                        )
                    )

    return doc


def anselm_postprocess(tok):

    for tok_anno in tok.tok_annos:
        # remove comment and boundary
        tok_anno.tags.pop("comment", None)
        tok_anno.tags.pop("boundary", None)
        tok_anno.flags.discard("boundary")

        # add "--" if morph is not set
        fill_annotation_column(tok_anno, "morph")

        # add norm if it is missing (???)
        # if 'norm' not in tok_anno.tags:
        #     print(tok_anno)

        # set norm_broad to norm if it is not set
        if "norm" in tok_anno.tags:
            fill_annotation_column(tok_anno, "norm_broad", tok_anno.tags["norm"])

        # rename norm_type-tags
        change_tags(
            tok_anno, "norm_type", {"f": "inflection", "s": "semantic", "x": "extinct"}
        )

        # fix erroneous tags
        change_tags(tok_anno, "pos", {"PDN": "PDS", "PIN": "PIS"})

    # add tokenization tags
    add_tokenization_tags(tok)

    # add punc tags
    # ANSELM: as yet no pre-edition punctuation
    # (and therefore no sent bounds discernible)
    # tok = add_punc_tags(tok)

    # alle Satzzeichen (type = p) auf $( setzen (wenn noch nichts gesetzt)
    update_punct_pos(tok)


def repair_header(doc, repair_infos):
    with open(repair_infos, "r", encoding="utf-8") as metadata_file:
        csvreader = csv.DictReader(metadata_file, dialect="excel-tab")
        for row in csvreader:
            if row["Sigle"].strip() == doc.sigle:

                new_header_string = list()
                lines_to_delete = [
                    "Text eingegeben",
                    "Datum",
                    "Bearbeiter",
                    "Text vorkollationiert",
                    "Text kollationiert",
                    "Lat. Passage",
                    "Kenn-Name",
                    "Präeditiert",
                    "Praeditiert",
                    "Grubert-Nummer",
                    "Datierung",
                    "Lokalisierung",
                    "Textart",
                    "Fassung",
                    "Bibliothek",
                    "Archiv",
                    "Signatur",
                    "Folio",
                    "Blatt",
                    "Edition",
                    "Provenienz",
                    "Literatur",
                    "vorhandener Text",
                    "Vorhandener Text",
                ]

                # delete unnecessary info from header
                for line in doc.header_string.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    elif any(line.startswith(x) for x in lines_to_delete):
                        continue
                    else:
                        new_header_string.append(line)

                # add important info to header
                new_keyval_strings = list()
                for key, val in row.items():
                    new_keyval_strings.append(key + ": " + val)

                doc.header_string = "\n".join(new_keyval_strings + new_header_string)


def anselm_document_postprocess(doc):
    anselm_correct_tokenization(doc)

    repair_infos = "../res/metadata_texts_20181220.csv"
    repair_header(doc, repair_infos)


def no_postprocess(doc):
    # do nothing
    return doc


def prepare_for_cora(tok):

    for tok_anno in tok.tok_annos:

        # undo renaming of norm_type-tags
        change_tags(
            tok_anno, "norm_type", {"inflection": "f", "semantic": "s", "extinct": "x"}
        )

        # remove empty morph annotations
        remove_annotation_column(tok_anno, "morph", value=DEFAULT_VAL)

        # remove norm_broad if it is identical with norm
        if (
            "norm_broad" in tok_anno.tags
            and tok_anno.tags["norm_broad"] == tok_anno.tags["norm"]
        ):
            remove_annotation_column(
                tok_anno, "norm_broad", tok_anno.tags["norm_broad"]
            )
