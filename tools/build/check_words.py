"""Independent letters-and-digits check: each section PDF against the file git holds for it.

    python check_words.py ~/Documents/united-states-northern-mariana-islands-law-build

The source side reads each PDF with PyMuPDF's plain `page.get_text()` and nothing from parse.py or build.py. It
removes, by its own simple rules, only what the build leaves out by design: the running heads in the first lines of
each page (lines written all in capitals, such as "TITLE 6: CRIMES AND CRIMINAL PROCEDURE" and "DIVISION 2:
CONTRABAND OFFENSES", and the bare "\u00a7 2301" page tab) and bare page numbers in the last lines of a page.
The git side is the section's file at main without its `## ` heading lines (those come from the Code's tree pages,
not from the PDF). Both are reduced to a multiset of letters and digits (casefolded), so order and markup do not
matter.

"missing" = in the PDF, not in git (dropped text). "extra" = in git, not in the PDF (text the build invented or
duplicated). A file is flagged when more than 0.1% is extra or more than 1% is missing.
"""
import csv
import io
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pymupdf

PDF = Path(__file__).resolve().parent / '.cache' / 'pdf'
PAGENO = re.compile(r'^\s*(\d{1,4}|-\s*\d+\s*-)\s*$')
HEADS = re.compile(r'^\s*(TITLE|DIVISION|PART)\s+\d+\s*:')
TAB = re.compile(r'^\s*\u00a7\u00a7?\s*[0-9][0-9A-Za-z.\-\u2013]*\s*$')


def letters(s: str) -> Counter:
    return Counter(c for c in s.casefold() if c.isalnum())


def source(pdf: Path) -> Counter:
    out = Counter()
    for page in pymupdf.open(pdf):
        lines = []  # (text, largest type size) per line of the plain text, in reading order
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                t = ''.join(s['text'] for s in line['spans'])
                if t.strip():
                    lines.append((t, max(s['size'] for s in line['spans'] if s['text'].strip()), line['bbox'][1]))
        head = True
        for i, (line, size, y) in enumerate(lines):
            if size < 10.6 and y < 130 and (TAB.match(line) or HEADS.match(line)
                                                     or line == line.upper() and re.search('[A-Z]', line)
                                                     and '_' not in line):  # a form's blank ("COMMENTS:____")
                continue  # a running head: small type at the top of the page
            head = False
            if i >= len(lines) - 2 and PAGENO.match(line):
                continue
            out += letters(line)
    return out


def main() -> None:
    repo = Path(sys.argv[1])

    def git(*a: str) -> str:
        return subprocess.run(['git', '-c', 'core.quotepath=false', '-C', str(repo), *a], capture_output=True,
                              text=True, encoding='utf-8', check=True).stdout

    rows = list(csv.DictReader(io.StringIO(git('show', 'main:data/files.csv'))))
    cat = subprocess.Popen(['git', '-C', str(repo), 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def blob(spec: str) -> str:
        cat.stdin.write(spec.encode('utf-8') + b'\n')
        cat.stdin.flush()
        header = cat.stdout.readline().split()
        data = cat.stdout.read(int(header[2]))
        cat.stdout.read(1)
        return data.decode('utf-8')

    results = []
    tot = miss_t = extra_t = 0
    for row in rows:
        text = '\n'.join(l for l in blob('main:' + row['file']).splitlines() if not l.startswith('## '))
        g = letters(text)
        rel = row['pdf'].split('/docs/', 1)[1]
        s = source(PDF / rel)
        miss, extra, total = sum((s - g).values()), sum((g - s).values()), sum(s.values()) or 1
        tot, miss_t, extra_t = tot + total, miss_t + miss, extra_t + extra
        results.append((extra / total, miss / total, row['file'], miss, extra, total,
                        ''.join((s - g).elements())[:40], ''.join((g - s).elements())[:40]))
    cat.stdin.close()
    bad = [r for r in results if r[0] > 0.001 or r[1] > 0.01]
    print(f'checked {len(results)} files, {tot} source letters and digits: {miss_t} missing '
          f'({100 * miss_t / max(1, tot):.4f}%), {extra_t} extra ({100 * extra_t / max(1, tot):.4f}%); '
          f'{len(bad)} files flagged; {sum(1 for r in results if not r[3] and not r[4])} exact')
    for r in sorted(bad, reverse=True)[:40]:
        print(f'  {r[2]}: missing {r[3]}/{r[5]} ({100 * r[1]:.2f}%) {r[6]!r}, extra {r[4]} ({100 * r[0]:.3f}%) {r[7]!r}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
