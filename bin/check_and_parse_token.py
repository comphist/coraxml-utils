#!/usr/bin/env python3
# coding: utf-8

import argparse

from coraxml_utils.parser import dialect_mapper
from coraxml_utils.modifier import trans_to_cora_json

if __name__ == "__main__":
    description = "Check and parse a CorA token. Can be used as backend for editing tokens in CorA."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('infile',
                        help='Eingabedatei (Token-Transkription)')
    parser.add_argument("-P", "--parser", choices=["rem", "anselm", "ref", "redi"],
                        default="ref", help="Token parser to use, default: %(default)s")
    args, _ = parser.parse_known_args()

    with open(args.infile) as f:
        token = f.read().strip()

    parsed_token = dialect_mapper[args.parser]().parse(token)

    print(trans_to_cora_json(parsed_token))

