#!/usr/bin/python3
# encoding: utf-8
# SPDX-FileCopyrightText: 2021 Felix C. Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

# --                                                            ; {{{1
#
# File        : fdroid-is-reproducible.py
# Maintainer  : Felix C. Stegerman <flx@obfusk.net>
# Date        : 2021-07-27
#
# Copyright   : Copyright (C) 2021  Felix C. Stegerman
# Version     : v0.0.1
# License     : AGPLv3+
#
# --                                                            ; }}}1

# requires: python3-click

import json
import os
import urllib.request
import time
import xml.etree.ElementTree as ET

from pathlib import Path

import click

INDEX_XML_URL = "https://f-droid.org/repo/index.xml"
VERIFIED_JSON_URL = "https://verification.f-droid.org/verified.json"
DATADIR = Path.home() / ".cache" / "fdroid-is-reproducible"
INDEX_XML = str(DATADIR / "index.xml")
VERIFIED_JSON = str(DATADIR / "verified.json")
METADATA_JSON = str(DATADIR / "metadata.json")


def download_index():
    if _outdated(INDEX_XML):
        with urllib.request.urlopen(INDEX_XML_URL) as fi:
            with open(INDEX_XML, "wb") as fo:
                fo.write(fi.read())
    if _outdated(METADATA_JSON):
        apps = {}
        with open(INDEX_XML) as fh:
            for e in ET.parse(fh).getroot():
                if e.tag != "application":
                    continue
                appid = e.find("id").text.strip()
                name = e.find("name").text.strip()
                version = e.find("marketversion").text.strip()
                vercode = int(e.find("marketvercode").text.strip())
                apps[appid] = dict(name=name, version=version, vercode=vercode)
        with open(METADATA_JSON, "w") as fh:
            json.dump(apps, fh)


def download_verified():
    if _outdated(VERIFIED_JSON):
        with urllib.request.urlopen(VERIFIED_JSON_URL) as fi:
            with open(VERIFIED_JSON, "wb") as fo:
                fo.write(fi.read())


def load_metadata():
    with open(METADATA_JSON) as fh:
        return json.load(fh)


def load_verified():
    with open(VERIFIED_JSON) as fh:
        return json.load(fh)


def _outdated(file):
    if not os.path.exists(file):
        return True
    if time.time() - os.stat(file).st_mtime > 24*60*60:
        return True
    return False


@click.command(help="FIXME")
@click.option("--search", is_flag=True)
@click.argument("query")
def cli(search, query):
    DATADIR.mkdir(parents=True, exist_ok=True)
    download_index()
    download_verified()
    apps = load_metadata()
    verified = load_verified()["packages"]
    if search:
        items = ((k, v) for k, v in apps.items()
                 if query.lower() in v["name"].lower())
    else:
        items = ((query, apps[query]),) if query in apps else ()
    for appid, data in items:
        total, status, last = 0, "not verified", (0, None)
        for app in verified.get(appid, []):
            assert app["verified"]
            vercode = int(app["local"]["versionCode"])
            if vercode == data["vercode"]:
                status = "successfully verified"
            total += 1
            if vercode > last[0]:
                last = (vercode, app["local"]["versionName"])
        print(appid + ":")
        print("  name:", data["name"])
        print("  current version:", data["version"])
        print("  current version code:", data["vercode"])
        print("  status:", status)
        print("  total verified:", total)
        if last[1]:
            print("  last verified version:", last[1])
            print("  last verified version code:", last[0])
        print()


if __name__ == "__main__":
    cli()

# vim: set tw=80 sw=4 sts=4 et fdm=marker :
