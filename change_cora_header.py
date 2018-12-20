# -*- coding: utf-8 -*-

import argparse
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

############################
#Function for pretty output.
def prettify(elem): 
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="", newl="")

############################

parser = argparse.ArgumentParser(description='Change CorA header.')
parser.add_argument('folder',
                    help='A folder containing CoraXML files.')
parser.add_argument('-a', "--add", help='A tab or csv file containing additional information to be added to the CoraXML header.')
parser.add_argument('-d', "--delete", action='store_true', default=False, help='Delete unwanted information from CoraXML header.')
args = parser.parse_args()

if args.add:
    if not os.path.isfile(args.add):
        print(args.add, "is not a file")
    else:
        additional_data = dict()
        additional_data_keys = list()
        for index,line in enumerate(open(args.add, mode="r", encoding="utf-8")):
            l = [col.strip() for col in line.split("\t")]
            if index == 0:
                for col in l:
                    additional_data_keys.append(col)
            else:
                additional_data[l[0]] = dict()
                for col in range(1, len(additional_data_keys)):
                    additional_data[l[0]][additional_data_keys[col]] = l[col]        

if not os.path.isdir(args.folder):
    print(args.folder, "is not a directory")
        
else:

    for filename in os.listdir(args.folder):

        print(filename)
        
        try:
            tree = ET.parse(args.folder+"/"+filename)
            root = tree.getroot()

            new_header_text = ""
            
            if args.delete:
               
                header_elem = root.find("./header")
                old_header_text = header_elem.text.strip().split("\n")

                for line in old_header_text:
                    
                    if not line.strip():
                        continue
                    
                    #Delete lines beginning with theses words.
                    elif any(line.strip().startswith(x) for x in ["Text eingegeben", \
                                                                  "Datum", "Bearbeiter", \
                                                                  "Text vorkollationiert:", \
                                                                  "Text kollationiert", \
                                                                  "Lat. Passage", "Kenn-Name", \
                                                                  "Präeditiert", "Praeditiert", \
                                                                  "Grubert-Nummer", "Datierung", \
                                                                  "Lokalisierung", "Textart", \
                                                                  "Fassung", "Bibliothek", "Archiv", \
                                                                  "Signatur", "Folio", "Blatt", \
                                                                  "Edition", "Provenienz", "Literatur", \
                                                                  "vorhandener Text", "Vorhandener Text"]):
                        continue

                    else:
                        new_header_text += line.strip() + "\n"
            else:
                pass

            if args.add:
                if not os.path.isfile(args.add):
                    pass
                
                else:
                    additional_text = ""
                    sigle = root.find("./cora-header").attrib["sigle"]
                    if sigle in additional_data:
                        for additional_info in additional_data_keys[1:]:
                            additional_text += additional_info + ": " + additional_data[sigle][additional_info] + "\n"
                    else:
                        print("No additional info for", filename)
                    new_header_text = additional_text + new_header_text

            if new_header_text:
                header_elem.text = new_header_text

                #Open the new xml file.
                xmlfile = open(args.folder+"/"+filename, mode="w", encoding="utf-8")

                #Print the tree.
                print(prettify(root), file=xmlfile)

                #Close new xml file.
                xmlfile.close()
            
        except ET.ParseError as e:
            print("Error reading file:", filename)
        

