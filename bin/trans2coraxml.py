#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import re
import argparse
from pathlib import Path
import logging
logging.basicConfig(format='%(levelname)s: %(message)s')

from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter


__version__ = "2018.01.09"

#Function reads in docx-file and returns the text with  annotations "+Q","@Q", "+H", "@H" and transcript information
# author: Helena Wedig
#       December 2017
### TODO refactor: remove hardcode parts from this function for shifttags and header

#Parameter: docx-file: infile
def importTextFromDocx(infile):

    import docx

    text_all = []
    doc = docx.Document(str(infile))
    name = infile.stem

    #variables to distinguish the fonts and to save the indices of beginning and end
    begin = False
    normal = False
    italic = False
    italic_begin = -1
    italic_end= -1
    marked_begin = -1
    marked_end = -1
    bibinfo_regex = re.compile(r"\[(\d*[rv]),(\d*)\]")
    line =  " "
    site = ""
    head = False

    #Checking which font is used in each paragraph
    #function saves beginning and end of questions and heading
    for sec in doc.paragraphs:
        for tok in range(len(sec.runs)):
            run = sec.runs[tok]
            content = run.text

            # If the text is written in italics,  the corresponding indices are saved.
            if run.font.italic == True and normal == False and italic == False:
                italic_begin = sec.text.index(content)
                italic = True
            # If the text is not written in italics and the preceeding element was written in italics, then the corresponding indices are saved as ending.
            elif run.font.italic != True and normal == False and italic != False:
                italic_end = sec.text.index(content)
                normal = True

            #If the text is marked and is not within a question sequence, the corresponding indices are saved.
            if run.font.highlight_color != None and begin == False:
                begin = True
                marked_begin = sec.text.index(content)
            #If the non-marked text follows a marked text, the corresponding indices are saved as ending.
            elif run.font.highlight_color == None and begin == True:
                begin = False
                marked_end = sec.text.index(content)

        match = bibinfo_regex.match(sec.text)
        #Saving the site and line numbers
        if match:
            site = "-" + match.groups()[0] + ","
            line = int(match.groups()[1])
                
        # Format the line number (adds 0)
        if line != " ":
            if int(line) < 10: line = "0" + str(line)
                
        # If the beginning of the heading is in this paragraph, "+H" is added.
        if italic_begin != -1 and italic_end == -1:
            text_all.append(sec.text[:italic_begin] + "+H\n" + sec.text[italic_begin:])
            italic_begin = -1
            head = True
        # If the ending of the heading is in this paragraph, "@H" is added.
        elif italic_begin == -1 and italic_end != -1:
            # If the italics end at the beginning of the next line, "@H" is added to the previous line.
            if italic_end == 0:
                if text_all[len(text_all)-1] != (""):   
                    text_all[len(text_all)-1] += "@H"
                else:   
                    text_all[len(text_all)-2] += "\n@H"
                if match:
                    text_all.append(name + site + str(line) + "\t" +  sec.text[match.end(0):])
                else:
                    text_all.append(name + site + str(line) + "\t" +  sec.text)
            else:   
                text_all.append(sec.text[:italic_end] + "\n@H" + sec.text[italic_end:])
            italic_end = -1
            head = False
        # If beginning and ending are in one line, both "+H" and "@H"are added in the line.
        elif italic_begin != -1 and italic_end  != -1:
            text_all.append(sec.text[:italic_begin] + "+H\n" + sec.text [:italic_end] + "\n@H" + sec.text[italic_end:])
            italic_begin = -1
            italic_end = -1
            head = False

        # If the beginning of the question is in this paragraph, "+Q" is added.
        elif marked_begin != -1 and marked_end == -1:
            if match:
                text_all.append(name + site + str(line) + "\t" + sec.text[match.end(0):marked_begin] + "+Q " + sec.text [marked_begin:])
            else:
                text_all.append(name + site + str(line) + "\t" + sec.text[:marked_begin] + "+Q " + sec.text [marked_begin:])
            marked_begin = -1
        # If the ending of the question is in this paragraph, "@Q" is added.
        elif marked_end != -1 and marked_begin == -1:
            # Adding the tags in the previous line, if it would be at the beginning of the next line
            if marked_end == 0:
                text_all[len(text_all)-1] += " @Q"
                text_all.append(name + site + str(line) + "\t" + sec.text)
            else:
                if match:
                    text_all.append(name + site + str(line) + "\t" + sec.text[match.end(0):marked_end] + " @Q" + sec.text [marked_end:])
                else:
                    text_all.append(name + site + str(line) + "\t" + sec.text[:marked_end] + " @Q" + sec.text [marked_end:])
            marked_end = -1
        # If beginning and ending are in one line, both "+Q" and "@Q"are added to the line.
        elif marked_begin != -1 and marked_end  != -1:
            if match:
                text_all.append(name + site + str(line) + "\t" + sec.text[match.end(0):marked_begin] + "+Q " + sec.text [:marked_end] + " @Q" + sec.text[marked_end:])
            else:
                text_all.append(name + site + str(line) + "\t" + sec.text[:marked_begin] + "+Q " + sec.text [:marked_end] + " @Q" + sec.text[marked_end:])

        # Else: Adding the text in the list
        else:
            # Excluding site information, if the line is included in the heading
            if head == False:
                if match:
                    text_all.append(name + site + str(line) + "\t" + sec.text[match.end(0):])
                else:
                    text_all.append(name + site + str(line) + "\t" + sec.text)
            else: text_all.append(sec.text)
        # Increasing line number
        if line != " ": 
            line = int(line) + 1

    # The paragraphs are joined together to one text
    return "\n".join(text_all)


if __name__ == "__main__":
    description = "Konvertiert eine Transkriptionsdatei ins CorA-XML-Format."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('infile',
                        help='Eingabedatei (Transkription)')
    parser.add_argument('outfile', nargs="?",
                        help='Ausgabedatei (XML)')
    # TODO: automatic tagging?
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
    if _: logging.warn("Unknown args: %s", _)

    MyImporter = create_importer("trans", args.parser)
    MyExporter = create_exporter("coraxml")

    print("~BEGIN CHECK")
    doc = None
    if os.path.splitext(args.infile)[-1].lower() == '.docx':
        trans = importTextFromDocx(Path(args.infile))
        doc = MyImporter.import_from_string(trans)
    else:
        with open(args.infile, "r", encoding="utf-8") as infile:
            doc = MyImporter.import_from_string(infile.read().replace("\ufeff", ""))


    if doc:
        print("~SUCCESS CHECK")

        print("~BEGIN XMLCALL")
        try:
            output_xml = MyExporter.export(doc)

            if not args.outfile:
                args.outfile = doc.sigle + ".xml"

            with open(args.outfile, "wb") as outfile:
                output_xml.write(outfile, xml_declaration=True,
                                 pretty_print=True, encoding='utf-8')

        except Exception as e:
            print("~ERROR XMLCALL")
            print(str(e))
            sys.exit(1)

    else:
        print("~ERROR CHECK")
        print("Dokument konnte nicht eingelesen werden.")


    print("~SUCCESS XMLCALL")
