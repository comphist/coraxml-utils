#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trans2trans.py
Adam Roussel

based on
convert_check.py
Florian Petran

"""

import re
import sys
import codecs
import argparse
import logging
logging.basicConfig(format='%(levelname)s: %(message)s')

from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter

__version__ = "2017.12.02"


def check_valid(self):
    
    in_tag, close_tag = OrderedDict(), None
    lastbib = {"full": "", "sigle": "", "page": "", "col": "", "side": "", "line": 0}

    for i, l in enumerate(self.text):
        if self.options.lineinfo:
            lastbib = self.check_bibinfo(lastbib, l, i)

        # first, remove K, E tags with content. they cannot span
        # multiple lines, and their content doesn't need to conform
        # to transcription rules.
        # many comment tags can follow each other with a single whitespace,
        # but since the following whitespace belongs to the comment, we have clean
        # as long as the regex matches
        myline = l["line"]
        for comment_tag in SHIFT_TAGS_ONELINE:
            comment_regex = re.compile("( |^)\+{0} [^@]+? @{0}( |$)".format(comment_tag))
            while comment_regex.search(myline):
                myline = comment_regex.sub(" +{0} @{0} ".format(comment_tag), myline)

        myline = myline.split(" ")
        self.check_shifttags(myline, in_tag, close_tag, l, i)

        # check if SHIFT_TAGS_ONELINE were all close at the end of the line
        in_tag_items = reversed(in_tag.items())
        for tag, index in in_tag_items:
            if tag in set(SHIFT_TAGS_ONELINE):
                self.report("Tag wasn't closed at end of line: " + tag, self.text[index], index)
                in_tag.popitem()
            else:
                break

    for tag, index in in_tag.items():
        self.report("Tag wasn't closed at end of text: " + tag, self.text[index], index)

    for e in self.errors:
        print(e)

    if not self.options.nowarnings:

        if self.errors and self.warnings:
            print("----", file=sys.stderr)
        for w in self.warnings:
            print(w, file=sys.stderr)

    if self.errors:
        exit(1)


# XXX the following method is an abomination, refactoring is needed
def check_bibinfo(self, lastbib, l, i):
    if not l["bibl"]:
        self.report("No Bibl. Info found", l, i)
        return lastbib
    elif not BIBINFO_FORMAT.search(l["bibl"]):
        self.report("Bibl. Info has incorrect format: >>{0}<<".format(l["bibl"]), l, i)
        return lastbib

    b = BIBINFO_FORMAT.search(l["bibl"]).groups()
    thisbib = dict(zip(["full", "sigle", "page", "side", "col", "line"],
                       [l["bibl"]] + list(b)))
    thisbib["line"] = int(thisbib["line"])

    if lastbib["sigle"] != thisbib["sigle"] and lastbib["sigle"]:
        self.report("Text sigle is inconsistent: {0} vs. {1}".format(lastbib["sigle"],
                                                                thisbib["sigle"]), l, i)

    # check lines
    if (thisbib["page"] == lastbib["page"] and 
        thisbib["side"] == lastbib["side"] and 
        thisbib["col"] == lastbib["col"]):
        if thisbib["line"] == lastbib["line"]:
            self.report("Duplicate line number: " + str(lastbib["line"]), l, i)
        elif thisbib["line"] != lastbib["line"] + 1:
            self.warn("Unexpected line: {0} followed by {1}".format(lastbib["full"],
                                                               l["bibl"]), l , i)
    else:
        if thisbib["line"] != 1:
            self.warn("Unexpected line: {0}{1}{2} doesn't begin with line 1 ({3}, {4})".format(
                thisbib["page"], thisbib["side"], thisbib["col"], lastbib["full"], l["bibl"]), l, i)

    # check columns
    if (thisbib["page"] == lastbib["page"] and 
        thisbib["side"] == lastbib["side"] and 
        thisbib["col"] != lastbib["col"]):
        if lastbib["col"] and thisbib["col"] != chr(ord(lastbib["col"]) + 1):
            self.warn("Unexpected column: {0} followed by {1} ({2}, {3})".format(lastbib["col"],
                                                                                thisbib["col"],
                                                                                lastbib["full"],
                                                                                l["bibl"]), l ,i)
    elif thisbib["page"] != lastbib["page"] or thisbib["side"] != lastbib["side"]:
        if thisbib["col"] != "a" and thisbib["col"]:
            self.warn("Unexpected column: {0}{1} doesn't begin with column a ({2}, {3})".format(
                 thisbib["page"], thisbib["side"], lastbib["full"], l["bibl"]), l, i)

    if thisbib["page"] != lastbib["page"] and lastbib["side"]:
        if thisbib["side"] != "r":
            self.warn("Unexpected side: {0} doesn't begin with side r ({1}, {2})".format(thisbib["page"],
                                                                                    lastbib["full"],
                                                                                    l["bibl"]), l, i)

    return thisbib


def check_shifttags(self, my_line, in_tag, close_tag, l, i):
    for t in range(len(my_line)):
        if self.tag_open.search(my_line[t]):
            current_tag = self.tag_open.search(my_line[t]).group(2)
            in_tag[current_tag] = i
            my_line[t] = my_line[t].replace("+" + current_tag, "")
            continue

        if self.tag_close.search(my_line[t]):
            close_tag = self.tag_close.search(my_line[t]).group(2)
            my_line[t] = my_line[t].replace("@" + close_tag, "")
            try:
                last_tag = in_tag.popitem()
            except KeyError:
                last_tag = None

            if not last_tag:
                self.report("Tag {0} closes, but nothing was opened before.".format(close_tag), l, i)
                continue
            elif last_tag[0] != close_tag:
                self.report("Tag {0} closed by {1}".format(last_tag[0], close_tag), l, i)






if __name__ == '__main__':

    ap = argparse.ArgumentParser()
    ap.add_argument("inputfile", type=str, nargs='?')

    # these args need to be sent to exporter
    ap.add_argument('-p', '--preedpunc', choices=['leave', 'delete'], 
                    default='leave', help="Pre-edition punctuation")
    ap.add_argument('-r', '--preedtoken', choices=['leave', 'delete'], 
                    default='delete', help="Pre-edition characters for tokens (including (=))")
    ap.add_argument('-e', '--editnum', choices=['leave', 'delete'], 
                    default='delete', help="Edition/secondary numbering")
    ap.add_argument('-c', '--character', choices=['utf', 'simple', 'orig'],
                    default='utf', help="Character transformation type")
    ap.add_argument('-i', '--illegible', choices=['original', 'leave', 'delete', 'character'],
                    default='leave', help="What to do with illegible characters")
    ap.add_argument('-d', '--doubledash', choices=['leave', 'delete'],
                    default='delete', help="What to do with the doubledash")
    ap.add_argument('-s', '--strikethru', choices=['original', 'leave', 'delete'],
                    default='leave', help='What to do with struck words')

    # exporter
    ap.add_argument('-t', '--tokenize', choices=['none', 'historical', 'medium', 'all'],
                    default='medium', help="Tokenization")
    ap.add_argument("-T", "--taggermode", action="store_true",
                    help="Output one token per line, all tokenization, no bibinfo")
    ap.add_argument('-b', '--bibinfo', choices=['line', 'both', 'none'],
                    default='both', help="Bibliographic info in output")

    ap.add_argument("-o", "--output", help="Output to file")
    ap.add_argument("-W", "--nowarnings", action="store_true",
                    help="Don't output warnings for validity check")


    # these args need to go to the importer
    ap.add_argument("-L", "--lineinfo", action="store_false",
                    help="File comes without line info (sigle, line number, ...)")
    ap.add_argument('-S', '--nosyllab', action="store_true",
                    help="Don't resolve syllabification (double dash at line end)")
    ap.add_argument("-A", "--allowed", type=str, default="",
                    help="Additional allowed characters for validity check.")
    ap.add_argument("-R", "--preprocess", type=str,
                    help="File with regexes for preprocessing text.")
    ap.add_argument("-P", "--parser", choices=["rem", "anselm", "ref", "redi", "plain"],
                    default="plain", help="Token parser to use, default: %(default)s")
    args = ap.parse_args()

    if args.taggermode:
        args.tokenize = "all"
        args.bibinfo = "none"
    
    if args.nowarnings:
        logging.basicConfig(level=logging.ERROR)


    MyImporter = create_importer("trans", dialect=args.parser,
                                 lineinfo=args.lineinfo, nosyllab=args.nosyllab,
                                 allowed=args.allowed, preprocessing=None)

    doc = None
    with open(inputfile, "r", encoding="utf-8") as infile:
        doc = MyImporter.import_from_string(infile.read().replace("\ufeff", ""))

    MyExporter = create_exporter("trans", args.)

    outputfile = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    outputfile.write(MyExporter.export(doc))
    outputfile.close()


