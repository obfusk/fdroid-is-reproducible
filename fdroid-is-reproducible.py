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

# requires: git, python3-click, python3-yaml

import glob
import json
import os
import subprocess
import urllib.request

import click
import yaml

FDROIDDATA = "https://gitlab.com/fdroid/fdroiddata.git"
VERIFIED_JSON = "https://verification.f-droid.org/verified.json"


def download_metadata():
    if not os.path.exists("fdroiddata"):
        clone_cmd = "git clone --depth 1".split() + [FDROIDDATA]
        subprocess.run(clone_cmd, check=True)
    if not os.path.exists("metadata.json"):
        apps = {}
        for f in sorted(glob.glob("fdroiddata/metadata/*.yml")):
            with open(f) as fh:
                appid = os.path.splitext(os.path.basename(f))[0]
                data = yaml.safe_load(fh)
                name = data.get("Name") or data.get("AutoName") or ""
                apps[appid] = dict(
                    name=name, version=data["CurrentVersion"],
                    vercode=data["CurrentVersionCode"]
                )
        with open("metadata.json", "w") as fh:
            json.dump(apps, fh)


def download_verified():
    if not os.path.exists("verified.json"):
        with urllib.request.urlopen(VERIFIED_JSON) as fi:
            with open("verified.json", "wb") as fo:
                fo.write(fi.read())


def load_metadata():
    with open("metadata.json") as fh:
        return json.load(fh)


def load_verified():
    with open("verified.json") as fh:
        return json.load(fh)


@click.command(help="FIXME")
@click.option("--search", is_flag=True)
@click.argument("query")
def cli(search, query):
    download_metadata()
    download_verified()
    apps = load_metadata()
    verified = load_verified()["packages"]
    if search:
        items = ((k, v) for k, v in apps.items() if query in v["name"])
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
