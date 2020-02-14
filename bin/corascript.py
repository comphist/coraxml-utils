#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import getpass
import requests
import click


DEFAULT_BASE = "https://smokehead.linguistics.rub.de/cora/"


class CoraClient:
    def __init__(self, base_url=DEFAULT_BASE):
        self.username = input("Username: ")
        self.pw = getpass.getpass("Password: ")
        self.session = self.login()
        self.base_url = base_url

    def login(self):
        s = requests.Session()
        s.post(
            DEFAULT_BASE,
            data={
                "action": "login",
                "loginform[un]": self.username,
                "loginform[pw]": self.pw,
            },
        )
        return s

    def get_projects_and_files(self):
        """returns json"""
        r = self.session.get(self.base_url + "request.php?do=getProjectsAndFiles")
        return json.loads(r.content)

    def export_XML_file(self, file_id) -> str:
        """returns xml string"""
        r = self.session.get(
            self.base_url + "request.php",
            params={"do": "exportFile", "fileid": file_id, "format": "1"},
        )
        return r.content

    def upload_XML_file(self, project_id, filepath, tagsets):
        tagsets = {"linktagsets[{0}]".format(i): tag for i, tag in enumerate(tagsets)}
        r = self.session.post(
            self.base_url + "request.php",
            data={"action": "importXMLFile", "project": project_id, **tagsets},
            files=[("xmlFile", open(filepath, "r", encoding="utf-8"))],
        )
        return r.content


@click.group()
def cli():
    pass


@cli.command()
@click.argument("corpusnames", nargs=-1)
@click.option("-o", "outdir", default="./", help="Directory for exported files")
@click.option("-t", "--onlytexts", help="Just download these particular texts")
@click.option("-c", "--only-changed")
@click.option("-s", "--use-sigle")
def download(corpusnames, outdir, onlytexts, only_changed, use_sigle):

    # Log in
    client = CoraClient()

    # Get text info
    response = client.get_projects_and_files()
    if response["success"]:
        textinfo = response["data"]
    else:
        print("server-related error")
        exit(1)

    textname = "id"
    if use_sigle:
        textname = "sigle"

    textw = onlytexts.split(",") if onlytexts else list()

    for corpus in textinfo:
        if corpus["id"] in corpusnames:
            for text in corpus["files"]:
                if not textw or text[textname] in textw:
                    if not only_changed or text["changer_id"]:
                        # Get texts
                        print(
                            "exporting",
                            (text["id"], text["sigle"], text["fullname"]),
                            "...",
                        )
                        xmlstring = client.export_XML_file(text["id"])
                        with open(
                            os.path.join(outdir, text["id"] + ".xml"),
                            "w",
                            encoding="utf-8",
                        ) as outfile:
                            print(xmlstring.decode("utf-8"), file=outfile)

    print("done!")


@cli.command()
@click.argument("projectid")
@click.argument("filepath")
@click.argument("tagsets", nargs=-1)
def upload_file(projectid, filepath, tagsets):
    client = CoraClient()
    response = client.upload_XML_file(projectid, filepath, tagsets)
    print(response)
    print("done!")


@cli.command()
@click.argument("projectid")
@click.argument("path")
@click.argument("tagsets", nargs=-1)
def upload_files(projectid, path, tagsets):
    client = CoraClient()
    for filename in os.listdir(path):
        print(filename)
        response = client.upload_XML_file(projectid, path + "/" + filename, tagsets)
        print(response)
    print("done!")


if __name__ == "__main__":
    cli()
