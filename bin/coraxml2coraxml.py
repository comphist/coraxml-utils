#!/usr/bin/env python3
# coding: utf-8

from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter
from coraxml_utils.modifier import postprocess, no_postprocess, prepare_for_cora


if __name__ == "__main__":

    postprocess(
        create_importer(
            "coraxml",
            dialect="anselm",
            strict=False,
            tok_dipl_tag="tok_dipl",
            tok_anno_tag="tok_anno",
        ),
        create_exporter(
            "coraxml",
            options={
                # name mod -> tok_anno, dipl -> tok_dipl
                "dipl_tag_name": "dipl",
                "anno_tag_name": "mod",
            },
        ),
        prepare_for_cora
        # ,no_postprocess
    )
