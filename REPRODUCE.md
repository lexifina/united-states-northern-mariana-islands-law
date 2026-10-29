# Reproducing this repository

Built on 2026-10-29 from the Commonwealth Code pages and PDFs retrieved up to 2026-10-29, by the scripts in `tools/build/` (copied there as run). [`data/source-sha256.tsv`](data/source-sha256.tsv) lists the sha256 of the sitemap and of each PDF the build read, so a copy of those files can be checked byte for byte before rebuilding. How the files were retrieved is not part of this record.

| Script | sha256 |
| --- | --- |
| tree.py | `8ac6ac8750449baa210212dc97f88056cfeeef96ebae723f85333ac5a796a61a` |
| parse.py | `f7306b78f6519dd588451ca917e366e8dd2c3648b2383f5a02241da906c68d59` |
| build.py | `3110486232833c36b69a16b2d7f1cef6940e6e41963ef1dc2b30b9a011ba5dca` |
| docs.py | `55c28c7405ec18f5908b2134efe9a156f4991ce24de196fbc80fa5ff2851cd6e` |
| check_words.py | `a21cfee898f97d5da46c9599d332675136cd4d9855e4bcca8c2ec8be92f22389` |

Python 3.10 or later, PyMuPDF (`pip install pymupdf`) and git.

## Steps

With the retrieved sitemap, node pages and PDFs in place (each PDF matching its sha256 in `data/source-sha256.tsv`), and the day each was retrieved:

```sh
# 1. The tree, in the Code's order, from the node pages.
python tree.py
# 2. Read each PDF into paragraphs. One process: a pool of workers died on the build machine.
python parse.py
# 3. Build into a new, empty folder. --today dates the build and is the latest date allowed.
python build.py ../united-states-northern-mariana-islands-law-build --today 2026-10-29
```

With the same files, `build.py` gives the same commit hashes, because it writes the whole history in one `git fast-import` stream, sorted, with fixed dates and messages written as bytes.

## What the build produced

- 540 chapters (and divisions and parts holding sections directly) from 10 titles: 8,686 PDF pages.
- 7,195 section files: 7,156 numbered sections and 39 entries printed whole (reserved or repealed chapters, parts, forms).
- 1,079 commits: 1,055 consolidated (one per chapter per day) and one documentation commit.
- Dates from 2013-08-30 to 2026-10-29: 34 from upload stamps, 7,149 from PDF modification dates, 6 from PDF creation dates, 6 from the retrieval day.
- 9,062 public-law citations in the Source notes, of 1,238 public laws (`data/amendments.csv`).
- PDFs the build did not have: 0.

## Checks

```sh
python ../lexifina/scripts/global-law/check_corpus.py .     # the shared preflight
git rev-list --merges --count main                          # 0
git log --format='%(trailers:key=In-force,valueonly)' main | grep . | sort -c -r   # dates never go back
git log --format=%B main | grep -c $'\r'                    # 0
python tools/in_force_on.py 2026-10-29 "1 CMC 101"
```

The letters-and-digits check (`check_words.py` in the build scripts' folder) reads every PDF again with PyMuPDF's plain `page.get_text()`, shares no code with `parse.py`, and compares the letters and digits of each section with those of its file in git. Rebuilding twice from the same files gives the same `git rev-parse HEAD`.
