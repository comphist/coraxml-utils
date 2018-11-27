# README #

## coraxml_utils

coraxml_utils is a collection of tools to work with CorA-XML and different variants.
It consists of:

- a model for CorA-XML
- Importer to read different file formats and 
- Exporter to dump the content of a data model to certain formats 

These tools are used by a collection of scripts that are described in the next section.

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


### TODO

* Zweifelhafter Simplifizierungsregeln (möglicherweise müssen diese projektspezifisch
aufgefasst werden)
	* I005: `<mod id="a3220" trans="au\-$z*1|" utf="aūſz" simple="aunsz"/>`
	* I015: `<mod id="a42" trans="rote\-b\:g" utf="rotēb̈g" simple="rotenbg"/>`
* Validierung
	* Präeditionszeichen sind alleinstehend als Token nicht erlaubt


Zum neuen Parser/Token-Modell:

![character model overview](uebersicht.png)


* Parser
	- `__init__(str)` mit kwargs zum Einstellen einzelner Optionen
	- `parse(str) -> ParsedToken` (mit Unterklassen wie gehabt)

* ParsedToken
	- input string: all annotations as spans of this string
	- tokenizations also as spans (dipl/anno tokenizations)
	- utf string
	- simple string
	- (dipl_utf construction via application of dipl token spans to utf string)
	- other subtoken annotations (strikethrough, illegible, majuscules) also as spans
	- actual python references: `majs.append(input_string[0:2])`