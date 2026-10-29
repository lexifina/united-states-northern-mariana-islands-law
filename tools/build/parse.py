"""Read every cached Commonwealth Code section PDF into paragraphs.

    python parse.py [--workers N] [--force]   -> .cache/parsed/<pdf path with / as __>.json   (default: 1, sequential)

Per PDF: the running heads at the top of each page are removed (lines of 10.5 pt or less, in capitals or head patterns, ending above
y = 132, before the first line of text, such as "TITLE 6: CRIMES AND CRIMINAL PROCEDURE", "DIVISION 2: CONTRABAND
OFFENSES" and the "§ 2301" page tab), and bare page numbers at the foot. Lines on one baseline are merged. A
paragraph starts at a deeper first-line indent, after a short line (one that stops well before the right edge of
the lines around it), at an enumerator ("(b)", "(iii)") after a line that ends a sentence or clause, where the type
size changes, or after a vertical gap. Each paragraph keeps its lines (so build.py can decide which line-end hyphens
are real), whether it is bold and its left edge. The PDF's own dates (creationDate, modDate) are kept as `meta`.
"""
import json
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pymupdf

HERE = Path(__file__).parent
PDF = HERE / '.cache' / 'pdf'
OUT = HERE / '.cache' / 'parsed'

HEAD = re.compile(r'^(TITLE\s+\d+\b|DIVISION\s+\d+\b|PART\s+\d+\b|CHAPTER\s+\d+\b|ARTICLE\s+\d+\b|§§?\s*[0-9][0-9A-Za-z.\-–]*$)')
PAGENO = re.compile(r'^\s*(?:\d{1,4}|-\s*\d+\s*-)\s*$')
WS = re.compile(r'[ \t        ]+')
SOFT = re.compile('[­​﻿]')
ENUM = re.compile(r'^\(([0-9]{1,3}|[a-z]{1,4}|[A-Z]{1,3})\)\s')


def norm(s):
    return WS.sub(' ', SOFT.sub('', s)).strip()


def page_lines(page):
    raw = []
    for b in page.get_text('dict', flags=pymupdf.TEXT_PRESERVE_WHITESPACE)['blocks']:
        for l in b.get('lines', []):
            spans = [s for s in l['spans'] if s['text']]
            if spans and norm(''.join(s['text'] for s in spans)):
                raw.append({'x0': l['bbox'][0], 'x1': l['bbox'][2], 'y0': l['bbox'][1], 'y1': l['bbox'][3],
                            'spans': spans})
    raw.sort(key=lambda r: (round((r['y0'] + r['y1']) / 2), r['x0']))
    merged = []
    for r in raw:
        mid = (r['y0'] + r['y1']) / 2
        if merged and abs(mid - merged[-1]['mid']) < 2.5:
            m = merged[-1]
            m['parts'].append(r)
            m['y0'], m['y1'] = min(m['y0'], r['y0']), max(m['y1'], r['y1'])
            continue
        merged.append({'mid': mid, 'y0': r['y0'], 'y1': r['y1'], 'parts': [r]})
    out = []
    for m in merged:
        m['parts'].sort(key=lambda r: r['x0'])
        segs = []
        text, bold_chars, chars, size = '', 0, 0, 0
        for r in m['parts']:
            seg = ''.join(s['text'] for s in r['spans'])
            segs.append(norm(seg))
            for s in r['spans']:
                n = len(s['text'].strip())
                chars += n
                if n:
                    size = max(size, s['size'])
                if 'Bold' in s['font'] or (s['flags'] & 16):
                    bold_chars += n
        text = norm(' '.join(segs))
        out.append({'text': text, 'segs': segs, 'x0': round(min(r['x0'] for r in m['parts']), 1),
                    'x1': round(max(r['x1'] for r in m['parts']), 1), 'y0': round(m['y0'], 1),
                    'y1': round(m['y1'], 1), 'bold': chars > 0 and bold_chars >= chars * 0.9, 'size': round(size, 1)})
    return out


def is_head(l):
    """A running head: small type near the top of the page, each piece a head pattern or capitals (the heads are
    bold, but the page tab beside them is sometimes not: 3 CMC 2837)."""
    return l['size'] <= 10.5 and l['y1'] <= 132 and all(
        HEAD.match(s) or s == s.upper() for s in l['segs'] if s)


def parse(path):
    doc = pymupdf.open(path)
    pages = []
    dropped = {}
    for p in doc:
        pl = page_lines(p)
        kept = []
        body_started = False
        for i, l in enumerate(pl):
            if not body_started and is_head(l):
                dropped['head'] = dropped.get('head', 0) + 1
                continue
            body_started = True
            if PAGENO.match(l['text']) and l['y0'] > 700:
                dropped['page-number'] = dropped.get('page-number', 0) + 1
                continue
            kept.append(l)
        pages.append(kept)
    paras = []
    cur = None
    for pno, pl in enumerate(pages):
        for k, l in enumerate(pl):
            # the right edge of the text around this line, for telling a short (paragraph-ending) line
            near = [o['x1'] for o in pl[max(0, k - 4):k + 5] if abs(o['size'] - l['size']) < 0.6]
            l['ref'] = max(near) if near else l['x1']
            if cur is None:
                new = True
            else:
                prev = cur['last']
                if k == 0:
                    new = l['x0'] > prev['x0'] + 6 or prev['x1'] < prev['ref'] - 30 or bool(ENUM.match(l['text']) and prev['text'].endswith(('.', ':', ';')))
                else:
                    gap = l['y0'] - prev['y1']
                    new = (gap > max(4.5, 0.6 * (prev['y1'] - prev['y0'])) or l['x0'] > prev['x0'] + 6
                           or prev['x1'] < prev['ref'] - 30 or l['bold'] != prev['bold'] and l['text'].startswith('§')
                           or bool(ENUM.match(l['text'])) and prev['text'].endswith(('.', ':', ';')))
            if not new and abs(l['size'] - cur['last']['size']) > 0.6:
                new = True  # body text is 11 pt, the Source note and Commission Comment 10 pt
            if new:
                if cur:
                    paras.append(cur)
                cur = {'lines': [l['text']], 'bold': l['bold'], 'x0': l['x0'], 'page': pno + 1, 'size': l['size']}
            else:
                cur['lines'].append(l['text'])
                cur['bold'] = cur['bold'] and l['bold']
            cur['last'] = l
    if cur:
        paras.append(cur)
    for p in paras:
        p.pop('last', None)
    return {'pages': len(doc), 'dropped': dropped, 'paras': paras,
            'meta': {k: doc.metadata.get(k) or '' for k in ('title', 'creationDate', 'modDate')}}


def key(rel):
    return rel.replace('/', '__')


def one(rel):
    dst = OUT / (key(rel) + '.json')
    src = PDF / rel
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime and '--force' not in sys.argv:
        return rel, None
    try:
        r = parse(src)
    except Exception as e:  # noqa
        return rel, repr(e)
    tmp = dst.with_suffix('.tmp')
    tmp.write_text(json.dumps(r, ensure_ascii=False, sort_keys=True), encoding='utf-8', newline='\n')
    os.replace(tmp, dst)
    return rel, None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 1
    only = [a for a in sys.argv[1:] if a.endswith('.pdf')]
    names = only or sorted(p.relative_to(PDF).as_posix() for p in PDF.rglob('*.pdf'))
    errs = []
    if workers <= 1:
        results = map(one, names)
    else:
        ex = ProcessPoolExecutor(min(workers, 4))
        results = ex.map(one, names, chunksize=16)
    for i, (n, e) in enumerate(results):
        if e:
            errs.append((n, e))
        if i % 500 == 0:
            print(i, len(names), flush=True)
    print('done', len(names), 'errors', len(errs))
    for n, e in errs:
        print(' ', n, e)


if __name__ == '__main__':
    main()
