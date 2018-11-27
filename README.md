
# `coraxml_utils`

`coraxml_utils` is a collection of tools for processing CorA-XML and the various associated transcription languages for historical manuscripts.

It consists of:

- A model for CorA-XML
- A model for transcriptions
- Importers to read different file formats and 
- Exporters to dump the content of a data model to certain formats 
- Scripts for carrying out various combinations of these tasks.


# The data model

## Transcriptions

A transcription (`Trans`) consists of characters (`Char`) -- see the next section for more on characters. 

The central distinction that CorA-XML makes is that between *diplomatic* tokenizations and *modernized*, i.e. *annotatable*, tokenizations. CorA-XML additionally differentiates between *diplomatic* representations of transcribed text and *simplified* ASCII representations of the same text.

A `Trans` object thus has two essential methods: `tokenize_dipl` and `tokenize_anno` for producing the two tokenizations. The `tokenize_dipl` method produces a list of `DiplTrans` objects, which contain the UTF diplomatic representation of the transcriptions (accessible with `.utf()`). The `tokenize_anno` produces a list of `AnnoTrans` objects that contain the simplified ASCII representations (`.simple()`).


## Character classes

For the processing of transcriptions, `coraxml_utils` makes use of a 

![character model overview](charclasses.png)


## Corpus documents





### Scripts

- trans2coraxml.py
- coraxml2gatejson.py

### Importer

#### Transcriptions

This allows to read in a transcription following certain conventions and create a
CorA-XML for it.

Currently there are parsers for the following conventions:

- ReM
- ReF
- ReDi
- Anselm

#### CorA-XML

##### REM
##### Extended CorA-XML

TODO:
extends CorA-XML, adding span annotations and subtoken annotations


### Exporter

#### GATE JSON

This is the variant of Tweet JSON used by GATE.


# TODO

* Zweifelhafter Simplifizierungsregeln (möglicherweise müssen diese projektspezifisch
aufgefasst werden)
	* I005: `<mod id="a3220" trans="au\-$z*1|" utf="aūſz" simple="aunsz"/>`
	* I015: `<mod id="a42" trans="rote\-b\:g" utf="rotēb̈g" simple="rotenbg"/>`
* Validierung
	* Präeditionszeichen sind alleinstehend als Token nicht erlaubt
