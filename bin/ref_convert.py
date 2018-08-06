#!/usr/bin/env python3
# coding: utf-8
from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter
from coraxml_utils.modifier import postprocess, ref_postprocess

if __name__ == "__main__":

    postprocess(
        create_importer("coraxml", dialect="ref", strict=False),
        create_exporter("coraxml",
        ),
        ref_postprocess
    )
