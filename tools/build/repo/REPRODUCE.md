# Reproducing this repository

Built on {{TODAY}} from the Commonwealth Code pages and PDFs retrieved up to {{RETRIEVED}}, by the scripts in `tools/build/` (copied there as run). [`data/source-sha256.tsv`](data/source-sha256.tsv) lists the sha256 of the sitemap and of each PDF the build read, so a copy of those files can be checked byte for byte before rebuilding. How the files were retrieved is not part of this record.

| Script | sha256 |
| --- | --- |
| tree.py | `{{SHA_TREE_PY}}` |
| parse.py | `{{SHA_PARSE_PY}}` |
| build.py | `{{SHA_BUILD_PY}}` |
| docs.py | `{{SHA_DOCS_PY}}` |
| check_words.py | `{{SHA_CHECK_WORDS_PY}}` |

Python 3.10 or later, PyMuPDF (`pip install pymupdf`) and git.

## Steps

With the retrieved sitemap, node pages and PDFs in place (each PDF matching its sha256 in `data/source-sha256.tsv`), and the day each was retrieved:

```sh
# 1. The tree, in the Code's order, from the node pages.
python tree.py
# 2. Read each PDF into paragraphs. One process: a pool of workers died on the build machine.
python parse.py
# 3. Build into a new, empty folder. --today dates the build and is the latest date allowed.
python build.py ../united-states-northern-mariana-islands-law-build --today {{TODAY}}
```

With the same files, `build.py` gives the same commit hashes, because it writes the whole history in one `git fast-import` stream, sorted, with fixed dates and messages written as bytes.

## What the build produced

- {{UNITS}} chapters (and divisions and parts holding sections directly) from {{TITLES}} titles: {{PAGES}} PDF pages.
- {{FILES}} section files: {{SECTIONS}} numbered sections and {{WHOLE}} entries printed whole (reserved or repealed chapters, parts, forms).
- {{COMMITS}} commits: {{CONSOLIDATED}} consolidated (one per chapter per day) and one documentation commit.
- Dates from {{FIRST}} to {{LAST}}: {{UPLOAD_STAMPED}} from upload stamps, {{PDF_MODIFIED}} from PDF modification dates, {{PDF_CREATED}} from PDF creation dates, {{RETRIEVED_DATED}} from the retrieval day.
- {{CITATIONS}} public-law citations in the Source notes, of {{PUBLIC_LAWS}} public laws (`data/amendments.csv`).
- PDFs the build did not have: {{MISSING_PDFS}}.

## Checks

```sh
python ../lexifina/scripts/global-law/check_corpus.py .     # the shared preflight
git rev-list --merges --count main                          # 0
git log --format='%(trailers:key=In-force,valueonly)' main | grep . | sort -c -r   # dates never go back
git log --format=%B main | grep -c $'\r'                    # 0
python tools/in_force_on.py {{TODAY}} "1 CMC 101"
```

The letters-and-digits check (`check_words.py` in the build scripts' folder) reads every PDF again with PyMuPDF's plain `page.get_text()`, shares no code with `parse.py`, and compares the letters and digits of each section with those of its file in git. Rebuilding twice from the same files gives the same `git rev-parse HEAD`.
