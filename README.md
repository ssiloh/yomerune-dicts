# yomerune-dicts

The dictionaries of the app **yomerune** (an Android app that adds furigana to Japanese text and builds a word list), and the list the app downloads them from.

- `catalog.json`: the list of dictionaries (address, SHA-256, size, license, AI made or not). The app reads it when you tap 「목록 새로고침」 in its dictionary page, and
  checks every file it downloads against it.
- Release `dicts`: **unchanged copies** of dictionary files of other projects (JMdict by way of jmdict-simplified, JMdict-ko, Jitendex 日中辞典), under fixed names, so
  that the app needs to connect to GitHub only. Who made them and under which license: [NOTICE.md](NOTICE.md).
- `build.py` + `sources.json` + `.github/workflows/update.yml`: every Monday GitHub Actions looks at the latest release of each project, mirrors a file that changed and
  rewrites `catalog.json`. To add a dictionary, add a line to `sources.json` (the license must allow redistribution, and `NOTICE.md` must be updated).

The app connects only when you tap 「받기」 or 「목록 새로고침」, only to GitHub, and sends nothing but the address of the file. See https://ssiloh.github.io/yomerune-privacy/.
