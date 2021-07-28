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
import sys
import time
import urllib.request
import zipfile

from pathlib import Path

import click

INDEX_JAR_URL = "https://f-droid.org/repo/index-v1.jar"
VERIFIED_JSON_URL = "https://verification.f-droid.org/verified.json"
DATADIR = Path.home() / ".cache" / "fdroid-is-reproducible"
INDEX_JAR = DATADIR / "index-v1.jar"
INDEX_JSON = DATADIR / "index-v1.json"
VERIFIED_JSON = DATADIR / "verified.json"
METADATA_JSON = DATADIR / "metadata.json"
BLACKLIST = set(["org.fdroid.fdroid.privileged.ota"])


# FIXME: verify!
def download_index(force_refresh=False):
    if force_refresh or _outdated(INDEX_JSON):
        print("==> downloading index-v1.jar...", file=sys.stderr)
        with urllib.request.urlopen(INDEX_JAR_URL) as fi:
            with INDEX_JAR.open("wb") as fo:
                fo.write(fi.read())
        with zipfile.ZipFile(INDEX_JAR) as zf:
            with zf.open(INDEX_JSON.name) as fi:
                with INDEX_JSON.open("wb") as fo:
                    fo.write(fi.read())
        INDEX_JAR.unlink()
    if force_refresh or _outdated(METADATA_JSON):
        print("==> parsing index-v1.json...", file=sys.stderr)
        apps = {}
        with INDEX_JSON.open() as fh:
            data = json.load(fh)
            for app in data["apps"]:
                appid = app["packageName"]
                if appid in BLACKLIST:
                    continue
                name = (app.get("name") or app["localized"]["en-US"]["name"]).strip()
                version = app["suggestedVersionName"]
                vercode = int(app["suggestedVersionCode"])
                signed_by_developer = 0
                for pkg in data["packages"][appid]:
                    assert pkg["packageName"] == appid
                    if pkg["versionCode"] == vercode:
                        if pkg.get("srcname"):
                            signed_by_developer |= 1    # could be binaries
                        else:
                            signed_by_developer |= 2    # signatures
                assert signed_by_developer in (0, 1, 3)
                apps[appid] = dict(name=name, version=version, vercode=vercode,
                                   signed_by_developer=signed_by_developer)
        with METADATA_JSON.open("w") as fh:
            json.dump(apps, fh, sort_keys=True, indent=2)


def download_verified(force_refresh=False):
    if force_refresh or _outdated(VERIFIED_JSON):
        print("==> downloading verified.json...", file=sys.stderr)
        with urllib.request.urlopen(VERIFIED_JSON_URL) as fi:
            with VERIFIED_JSON.open("wb") as fo:
                fo.write(fi.read())


def load_metadata():
    with METADATA_JSON.open() as fh:
        return json.load(fh)


def load_verified():
    with VERIFIED_JSON.open() as fh:
        return json.load(fh)


def _outdated(path):
    return not path.exists() or time.time() - path.stat().st_mtime > 24 * 60 * 60


# FIXME
def _fmt_signed_by_developer(value):
    return {0: "missing", 1: "unknown", 3: "both"}[value]


# FIXME
@click.command(help="FIXME")
@click.option("--search", is_flag=True, help="FIXME")
@click.option("--force-refresh", is_flag=True, help="FIXME")
@click.argument("query")
def cli(search, force_refresh, query):
    DATADIR.mkdir(parents=True, exist_ok=True)
    download_index(force_refresh)
    download_verified(force_refresh)
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
        sbd = _fmt_signed_by_developer(data["signed_by_developer"])
        print(appid + ":")
        print("  name:", data["name"])
        print("  current version:", data["version"])
        print("  current version code:", data["vercode"])
        print("  signed by developer:", sbd)
        print("  status:", status)
        print("  total verified:", total)
        if last[1]:
            print("  last verified version:", last[1])
            print("  last verified version code:", last[0])
        print()


if __name__ == "__main__":
    cli()

# vim: set tw=80 sw=4 sts=4 et fdm=marker :
