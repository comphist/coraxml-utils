# README #


### Conventions

* classes -> CamelCase, everything else -> snake_case
* magic methods before other methods
* verbs are better than pro-verbs ("export" > "do_export", exception: "import" as
  it is a keyword)


### Was ist was?

* `bin/`
	* `convert_check.py`: Konvertiert und/oder prüft Transkriptionsdateien. 
	* `trans2coraxml.py`: Konvertiert Transkriptionsdateien nach CoraXML.
* `coraxml_utils/`
	* `coralib.py`: Objektmodell
* `test/`
	* `importer/`
	* ...