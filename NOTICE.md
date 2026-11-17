# Notice: who made these dictionaries

The release `dicts` of this repository holds **unchanged copies** of dictionary files made by other projects, and one dictionary that is **converted** (see below), for the app **yomerune** (an unofficial personal tool,
not related to LINE, Discord or X). Nothing is converted or edited here: `build.py` downloads the file of the latest release of each project, checks it is a zip and
uploads it under a fixed name. The files keep the licenses of their projects, listed below (a copy of each license text is in `licenses/`).

| File in the release | Made by | Source | License |
|---|---|---|---|
| `jmdict-dut.zip`, `jmdict-fre.zip`, `jmdict-ger.zip`, `jmdict-hun.zip`, `jmdict-rus.zip`, `jmdict-slv.zip`, `jmdict-spa.zip`, `jmdict-swe.zip` | JMdict by the Electronic Dictionary Research and Development Group (EDRDG), converted to JSON by **jmdict-simplified** (scriptin) | https://github.com/scriptin/jmdict-simplified | CC BY-SA 4.0; the EDRDG licence: https://www.edrdg.org/edrdg/licence.html |
| `jmdict-ko.zip` | **JMdict-ko** by kongchu2 (Korean meanings written by an AI; derived from JMdict) | https://github.com/kongchu2/jmdict-ko | CC BY-SA 4.0 (`licenses/jmdict-ko-LICENSE.txt`) |
| `jitendex-zh.zip` | **Jitendex 日中辞典** by greyindex (Chinese meanings written and revised by AI models; derived from Jitendex by Stephen Kraus, which is made from JMdict; example sentences from Tatoeba, CC BY 2.0 FR) | https://github.com/greyindex/jitendex-yomitan-zh | CC BY-SA 4.0 (`licenses/jitendex-zh-LICENSE.txt`, `licenses/jitendex-zh-NOTICE.md`) |
| `wty-jpn.zip` | **WTY** (wiktionary-to-yomitan, yomidevs): the Japanese Wiktionary (ja.wiktionary.org, extracted by kaikki.org / wiktextract) as a Yomitan dictionary, **converted here** | https://github.com/yomidevs/wiktionary-to-yomitan, https://huggingface.co/datasets/daxida/wty-release, https://kaikki.org/ | CC BY-SA 4.0 (the text of Wiktionary is CC BY-SA 4.0 and GFDL; the dataset card says CC BY-SA 4.0) |

The dictionaries are shared under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/): you may copy and redistribute them if you give the credit above, say if you
changed them and share your copy under the same license. The credits do not mean that the authors approve of this repository or of the app. The meanings of the AI made
dictionaries can be wrong; the app marks them `[AI]`.

`catalog.json` (the list of files, their SHA-256 and sizes) is data about these files and is free to use (CC0).

## What is converted: `wty-jpn.zip`
This file is **not** an unchanged copy. WTY's entries have no JMdict entry number, which the app needs to find a meaning, so `wty_pack.py` (in this repository) matches each WTY
entry to the JMdict entry it is about, by written form and reading, and writes the meanings in the jmdict-simplified shape. **Changes made:** only the list of meanings
(`glosses`) of each entry is taken, in plain text and cut at 160 characters; etymology, examples, notes and the inflected-form entries are left out; the entries of WTY that
could not be matched to one JMdict entry with certainty are left out; the meanings of the WTY entries that go to the same JMdict entry are put together (at most four).
The matching can be wrong for some words (the Wiktionary entries themselves are written by volunteers and may be wrong or odd). The app marks the dictionary `[비공식]`.
The license of the result is CC BY-SA 4.0, like its sources. The credit above does not mean that Wiktionary, kaikki.org or the authors of WTY approve of this repository or of the app.
