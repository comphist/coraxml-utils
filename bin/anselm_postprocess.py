#!/usr/bin/env python3
# coding: utf-8

from coraxml_utils.importer import create_importer
from coraxml_utils.exporter import create_exporter
from coraxml_utils.modifier import (
    postprocess,
    anselm_postprocess,
    anselm_document_postprocess,
)


if __name__ == "__main__":

    postprocess(
        create_importer("coraxml", dialect="anselm", strict=False),
        create_exporter(
            "coraxml",
            options={
                # name mod -> tok_anno, dipl -> tok_dipl
                "dipl_tag_name": "tok_dipl",
                "anno_tag_name": "tok_anno",
            },
        ),
        anselm_postprocess,
        anselm_document_postprocess,
    )
