# Script that extracts highlighted sequences from docx-Dateien
# author: Helena Wedig
#       December 2017 
# 

import sys
import os
import re
import argparse
from pathlib import Path

import docx


#Function reads in docx-file and returns the text with  annotations "+Q","@Q", "+H", "@H" and transcript information
#Parameter: docx-file: infile     txt-file = outfile
def importText(infile):
    text_all = []
    doc = docx.Document(str(infile))
    name = infile.stem

    #variables to distinct the fonts and to save the indices of beginning and end
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
            sec.text = sec.text[match.end(0):]
                
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
            text_all.append(name + site + str(line) + "\t" + sec.text[:marked_begin] + "+Q " + sec.text [marked_begin:])
            marked_begin = -1
        # If the ending of the question is in this paragraph, "@Q" is added.
        elif marked_end != -1 and marked_begin == -1:
            # Adding the tags in the previous line, if it would be at the beginning of the next line
            if marked_end == 0:
                text_all[len(text_all)-1] += " @Q"
                text_all.append(name + site + str(line) + "\t" + sec.text)
            else: text_all.append(name + site + str(line) + "\t" + sec.text[:marked_end] + " @Q" + sec.text[marked_end:])
            marked_end = -1
        # If beginning and ending are in one line, both "+Q" and "@Q"are added to the line.
        elif marked_begin != -1 and marked_end  != -1:    text_all.append(name + site + str(line) + "\t" + sec.text[:marked_begin] + "+Q " + sec.text [:marked_end] + " @Q" + sec.text[marked_end:])

        # Else: Adding the text in the list
        else:
            # Excluding site information, if the line is included in the heading
            if head == False: 
                text_all.append(name + site + str(line) + "\t" + sec.text)
            else: 
                text_all.append(sec.text)
        # Increasing line number
        if line != " ": 
            line = int(line) + 1
            
    # The paragraphs are joined together to one text
    return "\n".join(text_all)


if __name__ == "__main__":

    ap = argparse.ArgumentParser(description=("Script that extracts " +
                                              "highlighted sequences " + 
                                              "from docx-Dateien"))

    ap.add_argument("input_files", nargs="+", help="input file paths")
    ap.add_argument("-o", "--outputdir", default=".",
                    help='output directory (default: %(default)s)')
    args = ap.parse_args()

    outputdir = Path(args.outputdir)

    for path in args.input_files:
        mypath = Path(path)
        print("processing", mypath.stem, "...")
        output = importText(mypath)
        outpath = outputdir / Path(mypath.stem + ".txt")
        with open(outpath, "w", encoding="utf-8") as outfile:
            print(output, file=outfile)
