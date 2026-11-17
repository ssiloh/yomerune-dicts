# Notice: who made these dictionaries

The release `dicts` of this repository holds **unchanged copies** of dictionary files made by other projects, for the app **yomerune** (an unofficial personal tool,
not related to LINE, Discord or X). Nothing is converted or edited here: `build.py` downloads the file of the latest release of each project, checks it is a zip and
uploads it under a fixed name. The files keep the licenses of their projects, listed below (a copy of each license text is in `licenses/`).

| File in the release | Made by | Source | License |
|---|---|---|---|
| `jmdict-dut.zip`, `jmdict-fre.zip`, `jmdict-ger.zip`, `jmdict-hun.zip`, `jmdict-rus.zip`, `jmdict-slv.zip`, `jmdict-spa.zip`, `jmdict-swe.zip` | JMdict by the Electronic Dictionary Research and Development Group (EDRDG), converted to JSON by **jmdict-simplified** (scriptin) | https://github.com/scriptin/jmdict-simplified | CC BY-SA 4.0; the EDRDG licence: https://www.edrdg.org/edrdg/licence.html |
| `jmdict-ko.zip` | **JMdict-ko** by kongchu2 (Korean meanings written by an AI; derived from JMdict) | https://github.com/kongchu2/jmdict-ko | CC BY-SA 4.0 (`licenses/jmdict-ko-LICENSE.txt`) |
| `jitendex-zh.zip` | **Jitendex 日中辞典** by greyindex (Chinese meanings written and revised by AI models; derived from Jitendex by Stephen Kraus, which is made from JMdict; example sentences from Tatoeba, CC BY 2.0 FR) | https://github.com/greyindex/jitendex-yomitan-zh | CC BY-SA 4.0 (`licenses/jitendex-zh-LICENSE.txt`, `licenses/jitendex-zh-NOTICE.md`) |

The dictionaries are shared under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/): you may copy and redistribute them if you give the credit above, say if you
changed them and share your copy under the same license. The credits do not mean that the authors approve of this repository or of the app. The meanings of the AI made
dictionaries can be wrong; the app marks them `[AI]`.

`catalog.json` (the list of files, their SHA-256 and sizes) is data about these files and is free to use (CC0).
