# Reproducing this repository

Built on 2026-10-29 from the Commonwealth Code pages and PDFs retrieved up to 2026-10-29, by the scripts in `tools/build/` (copied there as run).

| Script | sha256 |
| --- | --- |
| fetch.py | `c116ef27577b18daf9ca32cffc38a04eab4d4f67be9c5cb244f81ce35a4d5533` |
| tree.py | `1da5c26abde76711c3ee1bfe04ff5242de49b63ca964bbff0b7c88c62bdce58a` |
| parse.py | `d1e80e19ad361aefd3b35109b24927747f5e6d6f28100a5dc60fb39ea474eebc` |
| build.py | `8d29d5b6d7029336a700d3430a2f64a0919d6822ab6e7355c08a8eb35496314a` |
| docs.py | `358d685084a9c97ea83473635c925ec02a336ac59a203e8694599b70e43dc5ac` |
| check_words.py | `475121d8f9acc794efad2ea2712e5b8de1a1232bbb230c51d6179c835f6d0c08` |

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
python build.py ../united-states-northern-mariana-islands-law-build --today 2026-10-29
```

## robots.txt, terms and bulk data


## Fetch rate

robots.txt sets no Crawl-delay. `fetch.py` runs one process with at most 4 requests open at a time to `cnmilaw.gov`: first the 8,503 node pages, then the PDFs they link. A failed request is retried up to 5 times, waiting 5 to 25 s. A 404 is recorded and not asked again. The scripts call `curl --compressed` and keep every file under `.cache/` (git-ignored). [`data/source-sha256.tsv`](data/source-sha256.tsv) lists the sha256 of the sitemap and of each PDF. With the same files, `build.py` gives the same commit hashes, because it writes the whole history in one `git fast-import` stream, sorted, with fixed dates and messages written as bytes.

## What the build produced

- 419 chapters (and divisions and parts holding sections directly) from 9 titles: 6,859 PDF pages.
- 5,638 section files: 5,601 numbered sections and 37 entries printed whole (reserved or repealed chapters, parts, forms).
- 806 commits: 805 consolidated (one per chapter per day) and one documentation commit.
- Dates from 2013-08-30 to 2026-10-29: 34 from upload stamps, 5,592 from PDF modification dates, 6 from PDF creation dates, 6 from the retrieval day.
- 7,200 public-law citations in the Source notes, of 1,046 public laws (`data/amendments.csv`).
- PDFs not yet fetched when this was built: 1,558.

## Checks

```sh
python ../lexifina/scripts/global-law/check_corpus.py .     # the shared preflight
git rev-list --merges --count main                          # 0
git log --format='%(trailers:key=In-force,valueonly)' main | grep . | sort -c -r   # dates never go back
git log --format=%B main | grep -c $'\r'                    # 0
python tools/in_force_on.py 2026-10-29 "1 CMC 101"
```

The letters-and-digits check (`check_words.py` in the build scripts' folder) reads every PDF again with PyMuPDF's plain `page.get_text()`, shares no code with `parse.py`, and compares the letters and digits of each section with those of its file in git. Rebuilding twice from the same cache gives the same `git rev-parse HEAD`.
