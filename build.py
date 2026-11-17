#!/usr/bin/env python3
"""Mirrors the dictionaries of sources.json into the rolling release `dicts` of this repository, makes the dictionaries that are converted, and writes catalog.json.

Run by .github/workflows/update.yml (every Monday and on demand); needs the `gh` command and GH_TOKEN. Two kinds of source:

 * mirrored: the latest release of the upstream project is downloaded UNCHANGED (when it is not the one already mirrored: GitHub gives the SHA-256 of a release
   file), checked to be a zip and uploaded under a fixed name (<id>.zip).
 * convert "wty": a WTY dictionary (Wiktionary -> Yomitan, hosted on Hugging Face) is given the numbers of the JMdict entries it is about (wty_pack.py) and
   written as a pack of the jmdict-simplified shape. It is made again only when the revision of WTY or the release of JMdict changed (the output is the same bytes
   for the same input, so an unchanged pack is not uploaded again either).

catalog.json lists every dictionary with the address of its file in this repository's release, its SHA-256 and size; the app (yomerune) reads it and checks every
file against it. The licenses stay those of the upstream projects (NOTICE.md, licenses/).

usage: python3 -I build.py [--no-upload]
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # `python3 -I` does not put the folder of the script on the path; wty_pack.py is in this repository

import wty_pack  # noqa: E402
REPO = os.environ.get("GITHUB_REPOSITORY", "ssiloh/yomerune-dicts")
MAX_BYTES = 150 * 1024 * 1024  # the biggest file the app takes (DictCatalog.MAX_BYTES)
UPLOAD = "--no-upload" not in sys.argv
UA = "yomerune-dicts-builder"
HF = "https://huggingface.co/datasets/daxida/wty-release/resolve/main/latest/"


def gh_json(path):
    return json.loads(subprocess.check_output(["gh", "api", path], text=True))


def http(url, retries=4):
    """A response of the address; waits and tries again when the host says 'too many requests' or is busy."""
    for n in range(retries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=300)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and n + 1 < retries:
                time.sleep(20 * (n + 1))
                continue
            raise


def download(url, dest):
    h = hashlib.sha256()
    n = 0
    with http(url) as r, open(dest, "wb") as f:
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


def sha_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def mirrored(s, prev, dist, changed):
    rel = gh_json("repos/%s/releases/latest" % s["repo"])
    pat = re.compile(s["asset"])
    assets = sorted((a for a in rel["assets"] if pat.search(a["name"])), key=lambda a: a["name"])
    if not assets:
        print("NO ASSET for", s["id"], "in", rel["tag_name"])
        return prev  # keep what is mirrored
    a = assets[-1]
    digest = (a.get("digest") or "").replace("sha256:", "")
    if prev and digest and digest == prev["sha256"] and a["size"] == prev["size"]:
        print("unchanged", s["id"])
        return prev
    out = dist / (s["id"] + ".zip")
    sha, n = download(a["browser_download_url"], out)
    if digest and digest != sha:
        raise SystemExit("%s: the download does not match the SHA-256 GitHub gives" % s["id"])
    if out.read_bytes()[:2] != b"PK":
        raise SystemExit("%s: not a zip file" % s["id"])
    if prev and prev["sha256"] == sha:
        out.unlink()
        print("unchanged (downloaded)", s["id"])
        return prev
    changed.append(out)
    print("mirrored", s["id"], n, sha[:12], rel["tag_name"])
    return {
        "id": s["id"], "kind": s["kind"], "code": s["code"], "name": s["name"], "project": s["project"],
        "url": "https://github.com/%s/releases/download/%s/%s.zip" % (REPO, TAG, s["id"]), "sha256": sha, "size": n,
        "license": s["license"], "ai": s["ai"], "version": rel["tag_name"], "page": "https://github.com/" + s["repo"],
    }


class Jmdict:
    """The JMdict release (jmdict-simplified, English file: it has every entry with its written forms and readings), loaded once when a conversion needs it."""

    def __init__(self, repo):
        self.rel = gh_json("repos/%s/releases/latest" % repo)
        self.tag = self.rel["tag_name"]
        self.forms = None
        self.version = ""

    def load(self, work):
        if self.forms is None:
            a = next(x for x in self.rel["assets"] if re.match(r"^jmdict-eng-[0-9].*\.json\.zip$", x["name"]))
            path = work / "jmdict-eng.zip"
            download(a["browser_download_url"], path)
            self.forms, self.version = wty_pack.load_jmdict(path)
            path.unlink()
        return self.forms


def converted(s, prev, dist, changed, jm, work):
    w = s["wty"]
    idx = json.loads(http(HF + "index/wty-%s-%s-index.json" % (w["source"], w["target"])).read().decode("utf-8"))
    revision = str(idx["revision"])
    inputs = "wty %s + jmdict %s + rules %d" % (revision, jm.tag, wty_pack.RULES)
    if prev and prev.get("inputs") == inputs:
        print("unchanged", s["id"], inputs)
        return prev
    wty_zip = work / ("wty-%s-%s.zip" % (w["source"], w["target"]))
    download(HF + "dict/%s/%s/wty-%s-%s.zip" % (w["source"], w["target"], w["source"], w["target"]), wty_zip)
    meta = {"unofficial": True, "ai": False, "source": "Wiktionary (WTY, kaikki.org)", "license": "CC BY-SA 4.0", "url": "https://github.com/yomidevs/wiktionary-to-yomitan"}
    forms = jm.load(work)
    pack, stats, _ = wty_pack.convert(wty_zip, None, s["code"], meta, forms=forms, forms_version=jm.version)
    wty_zip.unlink()
    if len(pack["words"]) < s.get("min_entries", 1000):
        raise SystemExit("%s: only %d entries: something is wrong with the input" % (s["id"], len(pack["words"])))
    out = dist / (s["id"] + ".zip")
    wty_pack.write_zip(pack, out, s["id"] + ".json")
    sha, n = sha_of(out), out.stat().st_size
    for k, v in sorted(stats.items()):
        print("  %-34s %8d" % (k, v))
    entry = {
        "id": s["id"], "kind": s["kind"], "code": s["code"], "name": s["name"], "project": s["project"],
        "url": "https://github.com/%s/releases/download/%s/%s.zip" % (REPO, TAG, s["id"]), "sha256": sha, "size": n,
        "license": s["license"], "ai": False, "version": "wty-" + revision, "page": s["page"], "inputs": inputs,
    }
    if prev and prev["sha256"] == sha:
        out.unlink()
        print("unchanged (made again)", s["id"])
        prev = dict(prev)
        prev["inputs"] = inputs
        return prev
    changed.append(out)
    print("made", s["id"], n, sha[:12], inputs)
    return entry


def main():
    global TAG
    cfg = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
    TAG = cfg["tag"]
    prev = {}
    cat_file = HERE / "catalog.json"
    if cat_file.exists():
        for e in json.loads(cat_file.read_text(encoding="utf-8")).get("dictionaries", []):
            prev[e["id"]] = e
    dist = HERE / "dist"
    work = HERE / "work"
    dist.mkdir(exist_ok=True)
    work.mkdir(exist_ok=True)
    entries, changed = [], []
    jm = None
    for s in cfg["sources"]:
        if s.get("convert") == "wty":
            jm = jm or Jmdict(cfg["jmdict_repo"])
            e = converted(s, prev.get(s["id"]), dist, changed, jm, work)
        else:
            e = mirrored(s, prev.get(s["id"]), dist, changed)
        if e:
            entries.append(e)
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
        if subprocess.call(["gh", "release", "view", TAG, "-R", REPO], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            subprocess.check_call(["gh", "release", "create", TAG, "-R", REPO, "--title", "Dictionaries", "--latest=false", "--notes",
                                   "Copies of the dictionaries of other projects, for the app yomerune. See NOTICE.md for who made them and their licenses."])
        subprocess.check_call(["gh", "release", "upload", TAG, "-R", REPO, "--clobber"] + [str(c) for c in changed])
        print("uploaded", len(changed), "files")


main()
