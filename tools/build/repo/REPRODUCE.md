# Reproducing this repository

Built on {{TODAY}} from the Commonwealth Code pages and PDFs retrieved up to {{RETRIEVED}}, by the scripts in `tools/build/` (copied there as run).

| Script | sha256 |
| --- | --- |
| fetch.py | `{{SHA_FETCH_PY}}` |
| tree.py | `{{SHA_TREE_PY}}` |
| parse.py | `{{SHA_PARSE_PY}}` |
| build.py | `{{SHA_BUILD_PY}}` |
| docs.py | `{{SHA_DOCS_PY}}` |
| check_words.py | `{{SHA_CHECK_WORDS_PY}}` |

Python 3.10 or later, PyMuPDF (`pip install pymupdf`), git and curl.

## Steps

```sh
# 1. The sitemap and every node page of the Code (8,503 pages; resumable, cached under .cache/).
python fetch.py pages
# 2. The one PDF each section page links (about 7,000 PDFs; resumable).
python fetch.py pdfs
# 3. The tree, in the Code's order (.cache/tree.json).
python tree.py
# 4. Read each PDF into paragraphs (.cache/parsed/). One process: a pool of workers died on the build machine.
python parse.py
# 5. Build into a new, empty folder. --today dates the build and is the latest date allowed.
python build.py ../united-states-northern-mariana-islands-law-build --today {{TODAY}}
```

## robots.txt, terms and bulk data


## Fetch rate

robots.txt sets no Crawl-delay. `fetch.py` runs one process with at most 4 requests open at a time to `cnmilaw.gov`: first the 8,503 node pages, then the PDFs they link. A failed request is retried up to 5 times, waiting 5 to 25 s. A 404 is recorded and not asked again. The scripts call `curl --compressed` and keep every file under `.cache/` (git-ignored). [`data/source-sha256.tsv`](data/source-sha256.tsv) lists the sha256 of the sitemap and of each PDF. With the same files, `build.py` gives the same commit hashes, because it writes the whole history in one `git fast-import` stream, sorted, with fixed dates and messages written as bytes.

## What the build produced

- {{UNITS}} chapters (and divisions and parts holding sections directly) from {{TITLES}} titles: {{PAGES}} PDF pages.
- {{FILES}} section files: {{SECTIONS}} numbered sections and {{WHOLE}} entries printed whole (reserved or repealed chapters, parts, forms).
- {{COMMITS}} commits: {{CONSOLIDATED}} consolidated (one per chapter per day) and one documentation commit.
- Dates from {{FIRST}} to {{LAST}}: {{UPLOAD_STAMPED}} from upload stamps, {{PDF_MODIFIED}} from PDF modification dates, {{PDF_CREATED}} from PDF creation dates, {{RETRIEVED_DATED}} from the retrieval day.
- {{CITATIONS}} public-law citations in the Source notes, of {{PUBLIC_LAWS}} public laws (`data/amendments.csv`).
- PDFs not yet fetched when this was built: {{MISSING_PDFS}}.

## Checks

```sh
python ../lexifina/scripts/global-law/check_corpus.py .     # the shared preflight
git rev-list --merges --count main                          # 0
git log --format='%(trailers:key=In-force,valueonly)' main | grep . | sort -c -r   # dates never go back
git log --format=%B main | grep -c $'\r'                    # 0
python tools/in_force_on.py {{TODAY}} "1 CMC 101"
```

The letters-and-digits check (`check_words.py` in the build scripts' folder) reads every PDF again with PyMuPDF's plain `page.get_text()`, shares no code with `parse.py`, and compares the letters and digits of each section with those of its file in git. Rebuilding twice from the same cache gives the same `git rev-parse HEAD`.
