# The laws of the Northern Mariana Islands, as a git repository

The Commonwealth Code of the Northern Mariana Islands as a git repository: all 10 titles, in 540 chapters (and the divisions and parts that hold sections directly). The source is the [Commonwealth Code](https://cnmilaw.gov/commonwealth-code) published by the CNMI Law Revision Commission, the body the Code itself sets up to codify and publish the Commonwealth's laws (1 CMC §§ 3801–3810). There is one file per section (7,156 of them), with one paragraph per line, so `git blame` and `git diff` work line by line.

**What this repository is not, yet: a history.** The Commission publishes only the current text of each section, one PDF per section, and keeps no dated earlier versions online. So each section appears once, holding its current text, with one exception: when the Commission amends or adds a section it uploads a new PDF to a new address, and for 23 sections the PDF at the old address is still online. Those sections have that earlier text as their first version and the current text as a later commit, so `git diff` shows what the amendment changed (for most, PL 24-36 of 2026). Nothing else before the current text can be rebuilt from this source. New publications will be added from now on as later commits, so the history grows forward from here. The amendment history the Code prints is kept: the Source note under each section, naming each public law that enacted, amended or repealed it, is in the files and in [`data/amendments.csv`](data/amendments.csv).

The record holds 7,195 files, made by the Commission between 2013-08-30 and 2026-10-29, in 1,079 commits.

## A lawyer's questions as git commands

| Question | Command |
| --- | --- |
| What does 1 CMC § 101 say? | `python tools/in_force_on.py 2026-10-29 "1 CMC 101"` |
| The same, by folder | `python tools/in_force_on.py 2026-10-29 title-01/general-provisions/chapter-01 101` |
| A whole chapter, in order | `python tools/in_force_on.py 2026-10-29 title-01/general-provisions/chapter-01` |
| Which public laws a section's Source note names | `grep '^Source' title-06/division-02/chapter-03/2301.md` |
| Every section a public law touched, by the notes | `grep 'PL 24-36' data/amendments.csv` |
| Which sections cite 1 CMC § 3806 in their own text | `git grep -n '1 CMC § 3806'` |
| What changed in a chapter since this build (after later builds) | `git log -p -- title-01/general-provisions/chapter-01` |
| When the Commission made each section's PDF | [`data/files.csv`](data/files.csv) |

Files sit at `title-NN/division-NN/[part-NN/]chapter-NN/<section>.md`, following the Code's own tree (Title 1 starts with an unnumbered `general-provisions` division; a former, repealed chapter is `former-chapter-NN`). A section's number is unique within its title, so `1 CMC § 101` is `title-01/general-provisions/chapter-01/101.md`. A section file starts with any Article, Subarticle or lettered headings above it (`## Article 1. General Definitions.`), then the section's own line as printed (`§ 101. Northern Mariana Islands: Defined.`), then its paragraphs, one per line: `(a) ...`, `(1) ...`. Last come the Commission's notes, copied as printed: `Source: ...`, then the `Commission Comment:` (and, for a few sections, `Case Annotations:`). Each folder's `index.txt` lists its files in the Code's order. 39 entries the Commission prints as one PDF without a section number (a reserved or repealed chapter, a part, a form) are one file named after their heading, such as `chapter-02.md`.

Line-end hyphens: the PDFs are typeset with hyphenation. A hyphen at the end of a line, before a lower-case letter, is dropped when joining the lines ("Mari-" + "ana" = "Mariana"), unless the same hyphenated word occurs in the middle of a line somewhere in the Code ("long-term"), when it is kept.

## The dates, and which one we use

**Each section is dated by the day the Commission made its PDF**, at noon Chamorro Standard Time (UTC+10; the Northern Mariana Islands keep no daylight saving time). For a section the Commission amended or added recently, that is the upload time in the PDF's address (`cmc-amended/T01/8282-law-enforcement-officers-20260930-092559.pdf`: 30 September 2026; 34 files). For the rest it is the modification date recorded inside the PDF (7,149 files), or its creation date where that is all it has (6), or the retrieval day (6). The `Date-source:` trailer says which. One commit holds the sections of one chapter made on one day. The date is also in the `Consolidated:` and `In-force:` trailers.

It is a compilation date. It is not the date any public law took effect, and it does not prove the text was in force on that day, or was not in force before it. The Source notes give each public law's date where they print one (`PL 19-01 § 2 (June 16, 2015)`), and [`data/amendments.csv`](data/amendments.csv) lists it (1,804 of 9,062 citations). It does not convert one kind of date into the other.

`tools/in_force_on.py` answers for any date on or after a section's compilation date. For an earlier date it says there is no version, because the source has none.

## What "author" means

A section's first version is authored by `CNMI Law Revision Commission <law-revision-commission@cnmilaw.invalid>`, with the trailer `Kind: consolidated`. The address cannot exist. The author is the publisher of the compilation, not a lawmaker, and no line of a first version is credited to a public law, because without the earlier text nobody can tell which words a public law wrote. In the shared design for these repositories, a change is credited to an amending law only when the source shows the text before and after it. That is so for the 23 sections with an earlier PDF: where the new Source note names exactly one public law the earlier note did not, the replacing commit is `Kind: amendment`, `Amended-by: PL 24-36`, authored `PL 24-36 <pl-24-36@cnmi-legislature.invalid>`, so `git blame` names that law for the lines it changed. Otherwise the replacing commit is `Kind: unexplained` and authored by the Commission. Its date is the Commission's upload day, not the day the law took effect; the `Previous:` trailer gives the earlier PDF and its date. Later publications will be added the same way.

There are 1,055 consolidated commits, 20 amendment commits and 3 unexplained ones. The Source notes cite 1,238 distinct public laws in 9,062 citations; the latest cited is PL 24-38.

## What it does not show

- Any text before the current publication, apart from the 23 sections above. The Commission keeps no dated earlier versions online. When it amends a section it uploads a new PDF to a new address and links only that one from the Code's tree; the earlier PDF was found by asking for the section's old address (`/docs/cmc_section/T<title>/<section>.pdf`), which answered for 23 of the 34 amended or added sections (the others are new sections, with no old address).
- The Covenant, the Constitution of the Northern Mariana Islands, the Trust Territory Code, public laws as enacted, the Administrative Code and court rules. The Commission publishes these as separate collections.
- 1 section whose PDF is damaged as published, so no reader can open it (cmc_section/T1/2656.pdf; retrieved twice, the same bytes both times). It is left out.
- Nodes of the tree with no PDF (an empty chapter heading or two), pictures, and the layout of tables: a table's words and figures are kept as paragraphs of text, not as a grid. Running heads and page numbers are left out.
- Public laws the Commission has not yet worked into the Code. A section's Source note shows what has been.

This is a research aid. The Commission's PDFs are the published text, and for anything that matters read them, or the public laws themselves.

## How it is checked

`tools/build/` holds the build as it was run. [`data/source-sha256.tsv`](data/source-sha256.tsv) has the sha256 of the sitemap and every PDF the build read. The build is deterministic: from the same files it gives the same commit hashes. See [`REPRODUCE.md`](REPRODUCE.md). Before publishing, the build was checked for these things:
- the letters and digits of every section file were compared with those of its PDF, read separately with PyMuPDF's plain text by a script that shares no code with the build (`tools/build/check_words.py`);
- the text `tools/in_force_on.py` prints for sample sections matches the PDF;
- every commit's trailers parse, every commit is at noon Chamorro time, and there are no merges, no dates that go backwards and no dates after the build date;
- two builds from the same files give the same HEAD.

## How it is built

The build reads the Code's sitemap, every node page of the Code's tree (title, division, part, chapter, article, section) and the one PDF each section page links, as retrieved. `tree.py` rebuilds the tree from the pages' breadcrumbs and child lists, in the Code's order. `parse.py` reads each PDF with PyMuPDF, drops the running heads and page numbers, and joins the lines of each paragraph. `build.py` puts each section in its chapter's folder, puts Article headings on the file below them, lists the Source notes' public laws, and writes one commit per chapter per day with `git fast-import`. No AI model takes part in building or checking it.


## Reuse

The laws themselves belong to nobody. Under the government edicts doctrine, as the Supreme Court of the United States applied it in *Georgia v. Public.Resource.Org, Inc.*, 590 U.S. 255 (2020), works that legislators and judges make in their official capacity cannot be copyrighted, and that includes annotations made by an agent of the legislature as part of its legislative duties. The Northern Mariana Islands are a commonwealth in political union with the United States, and the federal Copyright Act applies there. That covers the public laws the Commonwealth Legislature enacts and the Code the Law Revision Commission compiles from them under 1 CMC §§ 3801–3810, a public body the Legislature set up for that purpose. The Commission's Source notes and Commission Comments are close to the annotations held uncopyrightable in that case, though the case was decided on Georgia's facts and no court has applied it to the Commonwealth Code. The Commission's website asserts no copyright beyond a footer notice and carries only a disclaimer of accuracy; it has no terms of use (checked 2026-10-29). **This repository is private for now.** See [`SOURCES.md`](SOURCES.md).

Lexifina's own contributions (the tools, the arrangement into files and the commit messages) are CC0. See [`LICENSE`](LICENSE).
