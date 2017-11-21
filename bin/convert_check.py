#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_check.py
Adam Roussel
Florian Petran

"""

import re
import sys
import codecs
import argparse
from itertools import chain
from collections import OrderedDict

from settings import *
from parsed_token import ParseError
# from character import convert, convert_utf, convert_simple

__version__ = "2017.11.15"

class TextConverter:

    def __init__(self, options):
        self.text = list()
        self.header = list()
        self.infile = open(options.inputfile, "r", encoding="utf8") if options.inputfile else sys.stdin
        self.outfile = open(options.output, "w", encoding="utf8") if options.output else codecs.getwriter('utf8')(sys.stdout.buffer)
        self.options = options
        self.errors = list()
        self.warnings = list()
        self.tag_open = re.compile(r"( |^)\+([" + SHIFTTAGS + r"])( |$)")
        self.tag_close = re.compile(r"( |^)@([" + SHIFTTAGS + r"])( |$)")
        self.preprocess = list() # TODO


    # read file into array
    # split from header, bibinfo
    def read_text(self):
        in_header = False
        try:
            for line in self.infile:
                line = line.strip().replace('\ufeff', '')

                if line == "+H":
                    in_header = True
                if in_header:
                    self.header.append(line)
                    in_header = not (line == "@H")
                    continue

                if not line:
                    continue

                # look for line info if it's supposed to be present
                if self.options.lineinfo:
                    line = line.split("\t")
                    if len(line) < 2:
                        bibinfo, line = "", " ".join(line)
                    else:
                        bibinfo, line, *_ = line
                else:
                    bibinfo = ""

                # apply preprocessor to line
                # here it's secure we do not operate on header or bibinfo
                line = self.preprocessor(line)

                # TODO: replace "line" with parsed_token version in order to simplify
                #       all conversions/processing below
                self.text.append({"bibl": bibinfo, "line": line.strip(), "orig": line.strip()})

            # if we finished reading the text and are still in the header,
            # something went horribly wrong.
            if in_header:
                print("ERROR: Header tag doesn't close, don't know where to begin the check.")
                print("\t\t>>> Add an appropriate closing header tag and run the check again.")
                exit(1)
        except TypeError:
            print("ERROR: Input file is empty")
            exit(1)


    def preprocessor(self, line):
        for pp in self.preprocess:
            line = line.sub(*pp)
        return line


    def process_text(self):
        # if self.options.target == "original":
        #     return None
        # else:
        for i, l in enumerate(self.text):
            # hyphenation:
            #   must be done before all other steps, otherwise
            #   tokenization might miss punctuation in combined tokens            
            if re.search(r"\(?=\)?", l["line"]) and not self.options.nosyllab:
                self.syllabification(l, i)
                line_dist = 2
                while re.search(r"[^|](\(=\)$|=\|?$)", l["line"]) and i < (len(self.text) - 1):
                    self.syllabification(l, i, line_dist)
                    line_dist += 1

            l = self.conversions(l, i)            



    def conversions(self, line, index):
        # comments need to be matched multiple times because
        # they can follow each other
        # with only one space in between
        if not self.options.leaveshift:
            for stag in SHIFT_TAGS_ONELINE:
                comment_regex = re.compile(r"( |^)\+" + stag + r".*?@" + stag + r"( |$)")
                while comment_regex.search(line["line"]):
                    line["line"] = comment_regex.sub("  ", line["line"])

            # the following tags need to be removed separately
            # because they may be nested with each other
            # in which case the leading space of one becomes the
            # trailing space of the other, but it can only be
            # matched once
            for stag in SHIFT_TAGS_MULTILINE:
                line["line"] = re.sub(r"( |^)[+@][" + stag + r"]( |$)", "  ", line["line"])


        # parse string and have object
        # 1. remove certain char types (obey options)
        # 2. tokenize
        # 3. construct string (handle brackets)
        # 4. return string w/char conversions
        try:
            line["line"] = str(ParsedToken(line["line"], self.options).tokenize())
        except ParseError as err:
            self.report(err.message, line, index)

        return line


    def syllabification(self, l, i, line_distance=1):
        # treat = and (=) at line end, or in a string if the only
        # thing that follows is a comment
        #
        # now if we detected a = in the line, there are several
        # possibilities.
        # first, it can be at the last token of the line. this is easy.
        # second, it can be at the last, but is followed by a comment.
        #         not quite as easy, but not too hard either
        # third, it can be at an arbitrary position in the middle of the
        #        line. why this is, i have no idea
        # fourth, it can be within a token. this is probably a transcription
        #         error of sorts, but it shouldn't crash the script
        # fifth, multiple dashes in the same line. not sure if this can happen
        # sixth, next_line can also have a dash, and contain only one word

        # explanation of dash_at_eol:
        # first case: (=) at string end, not preceded by |
        # second case: = at string end,
        #                surrounded by 0-2 <> or []
        #                not preceded by |
        #                optionally followed by | or ||
        dash_at_eol = re.compile(r"(?<!\|) ( \(=\) $ | [<\[]{0,2}=[\]>]{0,2} \|{0,2} $ )", re.X)
        if not dash_at_eol.search(l["line"]):
            # if we remove all comments, is = at EOL?
            #   => case 2
            if dash_at_eol.search(re.sub(r"\s\+[KE].+?\@[KE]", "", l["line"]).strip()):
                this_line = l["line"].split(" ")
                tok_pos = next(i for i, x in enumerate(this_line) if dash_at_eol.search(x))
                this_line = [this_line[:tok_pos + 1], this_line[tok_pos + 1:]]
            else:
                this_line = None
        else:
            this_line = [ l["line"].split(" ") ]

        # if we haven't set this_line above, there is no defined way
        # we can parse the = in this line, so we just ignore it
        if this_line and len(self.text) > (i + line_distance):
            next_line = self.text[i + line_distance]["line"].split(" ")

            syllabified_token = (this_line[0].pop().strip() + next_line.pop(0).strip()).strip()

            if self.options.doubledash != "leave":
                syllabified_token = re.sub(r"([^\(])={1,2}([^\)])", r'\1\2', syllabified_token)

            this_line[0].append(syllabified_token)

            self.text[i]["line"] = " ".join(chain.from_iterable(this_line))
            self.text[i + line_distance]["line"] = " ".join(next_line)


    def report(self, descr, lineobj, index):
        self.errors.append("ERROR: {0}".format(descr))
        self.errors.append("\t\t>> in line {0} ({1})".format(index, lineobj["bibl"])) 
        self.errors.append("\t\t>> original: {0}".format(lineobj["orig"]))
        self.errors.append("\t\t>> simplified: {0}".format(lineobj["line"]))


    def warn(self, descr, lineobj, index):
        self.warnings.append("WARNING: {0}".format(descr))
        self.warnings.append("\t\t>> in line {0} ({1})".format(index, lineobj["bibl"])) 
        self.warnings.append("\t\t>> original: {0}".format(lineobj["orig"]))
        self.warnings.append("\t\t>> simplified: {0}".format(lineobj["line"]))


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


    def print_file(self):
        if self.options.bibinfo == "both":
            print(*self.header, sep="\n", file=self.outfile)
            # print(file=self.outfile)  # empty line after header

        join_char = "\n" if self.options.taggermode else " "

        for l in self.text:
            line = [x for x in l["line"].split(" ") if x]
            if self.options.bibinfo in {"both", "line"}:
                bibstr = l["bibl"] + "\t"
            else:
                bibstr = ""

            if line:
                print(bibstr + join_char.join(line).strip(), file=self.outfile)


def main(myoptions):
    tc = TextConverter(myoptions)
    tc.read_text()
    tc.process_text()
    tc.check_valid()
    if not myoptions.checkvalid:
        tc.print_file()


if __name__ == '__main__':

    ap = argparse.ArgumentParser()
    ap.add_argument("inputfile", type=str, nargs='?')
    ap.add_argument('-t', '--tokenize', choices=['none', 'historical', 'medium', 'all'],
                    default='medium', help="Tokenization")
    ap.add_argument('-p', '--preedpunc', choices=['leave', 'delete'], 
                    default='leave', help="Pre-edition punctuation")
    ap.add_argument('-r', '--preedtoken', choices=['leave', 'delete'], 
                    default='delete', help="Pre-edition characters for tokens (including (=))")
    ap.add_argument('-e', '--editnum', choices=['leave', 'delete'], 
                    default='delete', help="Edition/secondary numbering")
    ap.add_argument('-c', '--character', choices=['utf', 'simple', 'orig'],
                    default='utf', help="Character transformation type")
    ap.add_argument('-b', '--bibinfo', choices=['line', 'both', 'none'],
                    default='both', help="Bibliographic info in output")
    ap.add_argument('-i', '--illegible', choices=['original', 'leave', 'delete', 'character'],
                    default='leave', help="What to do with illegible characters")
    ap.add_argument('-d', '--doubledash', choices=['leave', 'delete'],
                    default='delete', help="What to do with the doubledash")
    ap.add_argument('-S', '--nosyllab', action="store_true",
                    help="Don't resolve syllabification (double dash at line end)")
    ap.add_argument('-s', '--strikethru', choices=['original', 'leave', 'delete'],
                    default='leave', help='What to do with struck words')
    ap.add_argument("-L", "--lineinfo", action="store_false",
                    help="File comes without line info (sigle, line number, ...)")
    ap.add_argument("-T", "--taggermode", action="store_true",
                    help="Output one token per line, all tokenization, no bibinfo")
    ap.add_argument("-o", "--output", help="Output to file")
    ap.add_argument("-W", "--nowarnings", action="store_true",
                    help="Don't output warnings for validity check")
    ap.add_argument("-A", "--allowed", type=str, default="",
                    help="Additional allowed characters for validity check.")
    ap.add_argument("-R", "--preprocess", type=str,
                    help="File with regexes for preprocessing text.")
    ap.add_argument("-C", "--checkvalid", action="store_true",
                    help="Check if transcription is valid")
    ap.add_argument("-P", "--parser", choices=["rem", "anselm", "ref", "redi"],
                    default="ref", help="Token parser to use, default: %(default)s")
    args = ap.parse_args()

    if args.taggermode:
        args.tokenize = "all"
        args.bibinfo = "none"

    if args.parser == "ref":
        from parsed_token import RefToken as ParsedToken
    elif args.parser == "rem":
        from parsed_token import RemToken as ParsedToken
    elif args.parser == "redi":
        from parsed_token import RediToken as ParsedToken
    elif args.parser == "anselm":
        from parsed_token import AnselmToken as ParsedToken

    main(Options(**args.__dict__))
    exit(0)
