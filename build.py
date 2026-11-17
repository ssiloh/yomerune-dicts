#!/usr/bin/env python3
"""Mirrors the dictionaries of sources.json into the rolling release `dicts` of this repository and writes catalog.json.

Run by .github/workflows/update.yml (every Monday and on demand); needs the `gh` command and GH_TOKEN. For every source it reads the latest release of the
upstream project, and when its file is not the one already mirrored (by the SHA-256 GitHub gives for a release file, or by downloading it) it downloads the
file UNCHANGED, checks it is a zip, and uploads it under a fixed name (<id>.zip). catalog.json lists every dictionary with the address of its mirrored file, its
SHA-256 and size; the app (yomerune) reads it and checks every file against it. Nothing is converted or edited: the licenses stay those of the upstream
projects (NOTICE.md, licenses/).

usage: python3 -I build.py [--no-upload]
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = os.environ.get("GITHUB_REPOSITORY", "ssiloh/yomerune-dicts")
MAX_BYTES = 150 * 1024 * 1024  # the biggest file the app takes (DictCatalog.MAX_BYTES)
UPLOAD = "--no-upload" not in sys.argv
UA = "yomerune-dicts-builder"


def gh_json(path):
    return json.loads(subprocess.check_output(["gh", "api", path], text=True))


def download(url, dest):
    h = hashlib.sha256()
    n = 0
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        while True:
            b = r.read(1 << 16)
            if not b:
                break
            n += len(b)
            if n > MAX_BYTES:
                raise SystemExit("%s is bigger than %d bytes" % (url, MAX_BYTES))
            h.update(b)
            f.write(b)
    return h.hexdigest(), n


def main():
    cfg = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
    tag = cfg["tag"]
    prev = {}
    cat_file = HERE / "catalog.json"
    if cat_file.exists():
        for e in json.loads(cat_file.read_text(encoding="utf-8")).get("dictionaries", []):
            prev[e["id"]] = e
    dist = HERE / "dist"
    dist.mkdir(exist_ok=True)
    entries, changed = [], []
    for s in cfg["sources"]:
        rel = gh_json("repos/%s/releases/latest" % s["repo"])
        pat = re.compile(s["asset"])
        assets = sorted((a for a in rel["assets"] if pat.search(a["name"])), key=lambda a: a["name"])
        if not assets:
            print("NO ASSET for", s["id"], "in", rel["tag_name"])
            if s["id"] in prev:
                entries.append(prev[s["id"]])  # keep what is mirrored
            continue
        a = assets[-1]
        p = prev.get(s["id"])
        digest = (a.get("digest") or "").replace("sha256:", "")
        if p and digest and digest == p["sha256"] and a["size"] == p["size"]:
            entries.append(p)
            print("unchanged", s["id"])
            continue
        out = dist / (s["id"] + ".zip")
        sha, n = download(a["browser_download_url"], out)
        if digest and digest != sha:
            raise SystemExit("%s: the download does not match the SHA-256 GitHub gives" % s["id"])
        if out.read_bytes()[:2] != b"PK":
            raise SystemExit("%s: not a zip file" % s["id"])
        if p and p["sha256"] == sha:
            entries.append(p)
            out.unlink()
            print("unchanged (downloaded)", s["id"])
            continue
        changed.append(out)
        entries.append({
            "id": s["id"], "kind": s["kind"], "code": s["code"], "name": s["name"], "project": s["project"],
            "url": "https://github.com/%s/releases/download/%s/%s.zip" % (REPO, tag, s["id"]), "sha256": sha, "size": n,
            "license": s["license"], "ai": s["ai"], "version": rel["tag_name"], "page": "https://github.com/" + s["repo"],
        })
        print("mirrored", s["id"], n, sha[:12], rel["tag_name"])
    cat = {"format": 1, "updated": time.strftime("%Y-%m-%d", time.gmtime()), "dictionaries": entries}
    text = json.dumps(cat, ensure_ascii=False, indent=1) + "\n"
    old = cat_file.read_text(encoding="utf-8") if cat_file.exists() else ""
    # the date alone is not a change
    if re.sub(r'"updated": "[^"]*"', "", old) != re.sub(r'"updated": "[^"]*"', "", text):
        cat_file.write_text(text, encoding="utf-8")
        print("catalog.json written:", len(entries), "dictionaries")
    else:
        print("catalog.json is the same")
    if changed and UPLOAD:
        if subprocess.call(["gh", "release", "view", tag, "-R", REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            subprocess.check_call(["gh", "release", "create", tag, "-R", REPO, "--title", "Dictionaries", "--latest=false", "--notes",
                                   "Unchanged copies of the dictionaries of other projects, for the app yomerune. See NOTICE.md for who made them and their licenses."])
        subprocess.check_call(["gh", "release", "upload", tag, "-R", REPO, "--clobber"] + [str(c) for c in changed])
        print("uploaded", len(changed), "files")


main()
