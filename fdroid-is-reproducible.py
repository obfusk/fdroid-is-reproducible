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
# suggests: apksigner

import json
import subprocess
import sys
import time
import urllib.request
import zipfile

from pathlib import Path

import click

REPO_URL = "https://f-droid.org/repo"
INDEX_JAR_URL = f"{REPO_URL}/index-v1.jar"
VERIFIED_JSON_URL = "https://verification.f-droid.org/verified.json"
CACHEDIR = Path.home() / ".cache" / "fdroid-is-reproducible"
INDEX_JAR = CACHEDIR / "index-v1.jar"
INDEX_JSON = CACHEDIR / "index-v1.json"
VERIFIED_JSON = CACHEDIR / "verified.json"
METADATA_JSON = CACHEDIR / "metadata.json"
BLACKLIST = set(["org.fdroid.fdroid.privileged.ota"])
FDROID_DN = b"CN=FDroid, OU=FDroid, O=fdroid.org, L=ORG, ST=ORG, C=UK"


# FIXME: verify!
def download_index(force_refresh=False):
    if force_refresh or _outdated(INDEX_JSON):
        _download(INDEX_JAR_URL, INDEX_JAR)
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
                devsigned = 0
                for pkg in data["packages"][appid]:
                    assert pkg["packageName"] == appid
                    if pkg["versionCode"] == vercode:
                        if pkg.get("srcname"):
                            assert pkg["apkName"] == _apk_name(appid, pkg["versionCode"])
                            devsigned |= 1  # could be binaries
                        else:
                            devsigned |= 2  # signatures
                assert devsigned in (0, 1, 3)
                apps[appid] = dict(name=name, version=version, vercode=vercode,
                                   devsigned=devsigned)
        with METADATA_JSON.open("w") as fh:
            json.dump(apps, fh, sort_keys=True, indent=2)


def download_verified(force_refresh=False):
    if force_refresh or _outdated(VERIFIED_JSON):
        _download(VERIFIED_JSON_URL, VERIFIED_JSON)


def load_metadata():
    with METADATA_JSON.open() as fh:
        return json.load(fh)


def load_verified():
    with VERIFIED_JSON.open() as fh:
        return json.load(fh)


def _download(url, path):
    print(f"==> downloading {path.name}...", file=sys.stderr)
    with urllib.request.urlopen(url) as fi:
        with path.open("wb") as fo:
            fo.write(fi.read())


def _outdated(path):
    return not path.exists() or time.time() - path.stat().st_mtime > 24 * 60 * 60


# FIXME
def _fmt_devsigned(value):
    return {0: "missing", 1: "unknown", 3: "both"}[value]


def _apk_name(appid, vercode):
    return f"{appid}_{vercode}.apk"


# FIXME
def _try_harder_devsigned(appid, vercode):
    apk = _apk_name(appid, vercode)
    url = f"{REPO_URL}/{apk}"
    pth = CACHEDIR / apk
    cmd = "apksigner verify --print-certs --".split() + [str(pth)]
    _download(url, pth)
    try:
        p = subprocess.run(cmd, check=True, stdout=subprocess.PIPE)
        if FDROID_DN not in p.stdout:
            return "yes"
    finally:
        pth.unlink()
    return "no"


# FIXME
@click.command(help="FIXME")
@click.option("--search", is_flag=True, help="FIXME")
@click.option("--force-refresh", is_flag=True, help="FIXME")
@click.option("--try-harder", is_flag=True, help="FIXME")
@click.argument("query")
def cli(search, force_refresh, try_harder, query):
    CACHEDIR.mkdir(parents=True, exist_ok=True)
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
        sbd = _fmt_devsigned(data["devsigned"])
        if data["devsigned"] == 1 and try_harder:
            sbd = _try_harder_devsigned(appid, data["vercode"])
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
