#!/usr/bin/env python3
"""Gives the entries of a WTY dictionary (Wiktionary -> Yomitan, https://github.com/yomidevs/wiktionary-to-yomitan) the number of the JMdict entry they are about, and
writes them as a pack the app yomerune can import (the jmdict-simplified shape: words -> id -> sense -> gloss).

Why: the app finds the meaning of a word by its JMdict entry number. The entries of WTY have no such number (the `sequence` of every one is 0), so each WTY entry is
matched to a JMdict entry by its written form and its reading. A match that is not sure is not made: the entry is left out.

The rules (`match`), for a WTY entry with a written form W and a reading R (the entries of inflected forms, `non-lemma`, are left out):
  1. R is given: some JMdict entry has the pair (W, R)  -> that entry (when several have it and exactly one is common, the common one; else none).
     R is given but no entry has that pair: W is another word (or the reading of a kanji, not of a word)  -> none.
  2. R is not given: JMdict has W in exactly one entry -> that entry; in several and exactly one of them is common -> the common one; else none.
The senses of all the WTY entries that go to one JMdict entry are put together (the ones matched by the pair first), the same text once, at most MAX_SENSES.

usage: python3 -I wty_pack.py --wty wty-ja-ja.zip --jmdict jmdict-eng-X.json.zip --lang jpn --out wty-jpn.zip [--meta '{"...": ...}']
"""
import argparse
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict

MAX_SENSES = 4          # the app keeps 4 meanings of an entry
MAX_TEXT = 160          # one meaning of a Wiktionary entry can be a paragraph
ZIP_DATE = (2020, 1, 1, 0, 0, 0)  # fixed, so that the same input gives the same bytes (and the release is not uploaded again)


def hira(s):
    return "".join(chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in s)


# ---------------------------------------------------------------- JMdict
class Forms:
    """The written forms and the readings of JMdict: by_text[W] = {ids}, by_pair[(W, reading)] = {ids}, common[id]."""

    def __init__(self):
        self.by_text = defaultdict(set)
        self.by_pair = defaultdict(set)
        self.common = {}

    def add_word(self, w):
        wid = int(w["id"])
        kanji = [(k["text"], bool(k.get("common"))) for k in w.get("kanji", [])]
        kana = w.get("kana", [])
        self.common[wid] = any(c for _, c in kanji) or any(a.get("common") for a in kana)
        for k, _ in kanji:
            self.by_text[k].add(wid)
        for a in kana:
            r = hira(a["text"])
            self.by_text[a["text"]].add(wid)
            self.by_pair[(a["text"], r)].add(wid)  # the kana form is its own reading
            applies = a.get("appliesToKanji", ["*"])
            for k, _ in kanji:
                if applies == ["*"] or k in applies:
                    self.by_pair[(k, r)].add(wid)

    def pick(self, ids):
        """The one entry of [ids]: the only one, or the only common one; None when it is not clear."""
        if len(ids) == 1:
            return next(iter(ids))
        c = [i for i in ids if self.common.get(i)]
        return c[0] if len(c) == 1 else None

    def match(self, term, reading):
        """-> (kind, id); kind: 'pair', 'text' or None."""
        if term not in self.by_text:
            return None, None
        if reading:
            ids = self.by_pair.get((term, hira(reading)))
            if not ids:
                return None, None   # JMdict knows the form, but not with this reading: another word
            i = self.pick(ids)
            return ("pair", i) if i else (None, None)
        i = self.pick(self.by_text[term])
        return ("text", i) if i else (None, None)


def load_jmdict(path):
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.endswith(".json"))
        data = json.loads(z.read(name))
    f = Forms()
    for w in data["words"]:
        f.add_word(w)
    version = data.get("version", "")
    del data
    return f, version


# ---------------------------------------------------------------- WTY
def _plain(node):
    """The text of a structured-content node without its lists, examples and notes."""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(_plain(n) for n in node)
    if isinstance(node, dict):
        if node.get("tag") in ("ul", "ol", "details", "summary"):
            return ""
        return _plain(node.get("content"))
    return ""


def _norm(s):
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > MAX_TEXT:
        cut = s[:MAX_TEXT]
        for stop in ("。", "；", "、", ";", ",", " "):
            k = cut.rfind(stop)
            if k >= MAX_TEXT // 2:
                cut = cut[:k + (1 if stop == "。" else 0)]
                break
        s = cut.rstrip("、，,; ") + "…"
    return s


def glosses_of(definitions):
    """The meanings of a WTY entry: one text for each item of its list of glosses (not the etymology, not the examples)."""
    out = []

    def walk(n):
        if isinstance(n, dict):
            if n.get("tag") == "ol" and (n.get("data") or {}).get("content") == "glosses":
                for li in n.get("content") or []:
                    if isinstance(li, dict) and li.get("tag") == "li":
                        t = _norm(_plain(li.get("content")))
                        if len(t) >= 2:
                            out.append(t)
                return
            walk(n.get("content"))
        elif isinstance(n, list):
            for x in n:
                walk(x)

    for d in definitions:
        if isinstance(d, dict):
            walk(d.get("content"))
        elif isinstance(d, str):
            t = _norm(d)
            if len(t) >= 2:
                out.append(t)
    return out


def load_wty(path):
    """-> (index.json, rows); a row is (term, reading, tags, definitions)."""
    rows = []
    with zipfile.ZipFile(path) as z:
        index = json.loads(z.read("index.json"))
        for n in sorted(x for x in z.namelist() if re.match(r"term_bank_\d+\.json$", x)):
            for r in json.loads(z.read(n)):
                rows.append((r[0], r[1], str(r[2]).split(), r[5]))
    return index, rows


# ---------------------------------------------------------------- the pack
def convert(wty_path, jmdict_path, lang, meta=None, forms=None, forms_version=""):
    if forms is None:
        forms, forms_version = load_jmdict(jmdict_path)
    index, rows = load_wty(wty_path)
    by_id = {}                      # id -> {"pair": [texts], "text": [texts]}
    stats = Counter()
    for term, reading, tags, defs in rows:
        if "non-lemma" in tags:
            stats["skipped: inflected form"] += 1
            continue
        kind, wid = forms.match(term, reading)
        if wid is None:
            stats["left out: no sure JMdict entry"] += 1
            continue
        gl = glosses_of(defs)
        if not gl:
            stats["left out: no meaning"] += 1
            continue
        stats["matched by " + kind] += 1
        e = by_id.setdefault(wid, {"pair": [], "text": []})
        e[kind].extend(gl)
    words = []
    for wid in sorted(by_id):
        seen, senses = set(), []
        for t in by_id[wid]["pair"] + by_id[wid]["text"]:
            if t not in seen and len(senses) < MAX_SENSES:
                seen.add(t)
                senses.append({"gloss": [{"lang": lang, "text": t}]})
        if senses:
            words.append({"id": str(wid), "sense": senses})
    revision = str(index.get("revision", ""))
    pack = {
        "version": "wty-" + revision + (("+jmdict-" + forms_version) if forms_version else ""),
        "dictDate": revision.replace(".", "-"),
        "yomerune": meta or {},
        "words": words,
    }
    stats["entries of the pack"] = len(words)
    return pack, stats, index


def write_zip(pack, out_path, inner_name):
    text = json.dumps(pack, ensure_ascii=False, separators=(",", ":")) + "\n"
    zi = zipfile.ZipInfo(inner_name, ZIP_DATE)
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0o644 << 16
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(zi, text.encode("utf-8"))
    return len(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wty", required=True)
    ap.add_argument("--jmdict", required=True)
    ap.add_argument("--lang", required=True, help="3 letter code of the language of the meanings (jpn)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--meta", default="{}")
    a = ap.parse_args()
    pack, stats, _ = convert(a.wty, a.jmdict, a.lang, json.loads(a.meta))
    n = write_zip(pack, a.out, "wty-%s.json" % a.lang)
    for k, v in sorted(stats.items()):
        print("%-34s %8d" % (k, v))
    print("json %.1f MB" % (n / 1e6))


if __name__ == "__main__":
    main()
