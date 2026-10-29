"""Build the Northern Mariana Islands law repository from the Law Revision Commission cache.

    python fetch.py pages; python fetch.py pdfs; python tree.py; python parse.py
    python build.py C:/Users/alany/Documents/united-states-northern-mariana-islands-law-build --today 2026-10-29

The CNMI Law Revision Commission publishes the Commonwealth Code (CMC) at cnmilaw.gov as a tree of node pages, one
PDF per section. It publishes the current text of each section and keeps no dated past versions, so this record is
current-only (the Guam, Fiji and Turkey pattern):

1. Folders follow the Code: title-NN/division-NN/[part-NN/]chapter-NN/<section>.md. A chapter (or a division or part
   that holds sections directly) is one unit. Article, subarticle and lettered headings go on top of the next
   section file as `##` lines. A node that the Commission prints whole (a reserved chapter, a form) is one file
   named after its heading. Each file holds the PDF's text, one paragraph per line: the section line
   ("\u00a7 101. Northern Mariana Islands: Defined."), the text, the Source note and the Commission Comment.
2. Each file is dated by when the Commission made its PDF: the upload time in the path for sections it amended or
   added ("cmc-amended/T01/8282-...-20260930-092559.pdf"), otherwise the PDF's own modification date (modDate),
   otherwise its creation date. One commit per unit per such day, `Kind: consolidated`, authored by the Law Revision
   Commission, at noon Chamorro Standard Time (UTC+10, no daylight saving). No line is credited to a public law:
   the text before each amendment is not published. The Source notes are listed in data/amendments.csv.
3. Where the Commission's earlier PDF of an amended section is still online at its old address
   (.cache/old/, fetch.py old), that earlier text is committed first, on its own date, and the current text then
   replaces it as a later commit (`Kind: amendment` when the new Source note names exactly one public law that the
   old one did not, credited to it; otherwise `Kind: unexplained`).
4. A documentation commit closes the history, dated by the retrieval day. One git fast-import; same cache, same hashes.
"""
import argparse
import calendar
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CACHE = HERE / '.cache'
PARSED = CACHE / 'parsed'
SITE = 'https://cnmilaw.gov'
SLUG = 'united-states-northern-mariana-islands-law'
COMMITTER = ('Lexifina', SLUG + '@lexifina.com')
PUBLISHER = ('CNMI Law Revision Commission', 'law-revision-commission@cnmilaw.invalid')
TZ = '+1000'  # Chamorro Standard Time, UTC+10 all year: the Northern Mariana Islands keep no daylight saving time

PL = re.compile(r'(?<![A-Za-z.])P\.?\s?L\.?\s*(\d{1,2})\s*-\s*(\d{1,3})(?!\d)')
PL_DATE = re.compile(r'^[^()]{0,60}?\(([A-Z][a-z]{2,9}\.?\s*\d{1,2},?\s*\d{4})\)')
VERB = re.compile(r'(repealed\s*(?:/|and)\s*re-?enacted|re-?enacted|added|amended|repealed|renumbered|recodified|'
                  r'codified|enacted|deleted|substituted|redesignated|adopted|modified)', re.I)
MONTHS = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov',
                                      'dec'], 1)}
STAMPED = re.compile(r'/docs/cmc-(?:amended|added)/[^/]+/.*-(\d{4})(\d{2})(\d{2})-(\d{6})\.pdf$')


# ---------------------------------------------------------------------------------------------- tree

def kind(h):
    h = re.sub(r'^Former\s+', '', h)
    if h.startswith('\u00a7'):
        return 'section'
    m = re.match(r'(Title|Division|Part|Chapter|Subchapter|Sub-?[Aa]rticle|Article|Forms?|Appendix|Schedule)\b', h)
    if m:
        return m.group(1).lower().replace('-', '').rstrip('s') if m.group(1).lower() == 'forms' else \
            m.group(1).lower().replace('-', '')
    if re.match(r'[A-Z]\.\s', h):
        return 'letter'
    return 'other'


def slug(h, k):
    """'Title 2: Natural Resources' -> title-02; 'Division 4 Land Resources' -> division-04; 'Chapter 4A.' ->
    chapter-04A; 'Former Chapter 1.' -> former-chapter-01; 'General Provisions' -> general-provisions."""
    former = h.startswith('Former ')
    hh = re.sub(r'^Former\s+', '', h)
    m = re.match(r'(Title|Division|Part|Chapter|Article|Subarticle|Sub-Article|Subchapter)\s+([0-9]+)([A-Za-z]?)\b', hh)
    if m:
        s = '%s-%02d%s' % (m.group(1).lower().replace('-', ''), int(m.group(2)), m.group(3).upper())
    else:
        m = re.match(r'(Part|Article|Chapter|Division)\s+([A-Z])\b', hh)
        s = ('%s-%s' % (m.group(1).lower(), m.group(2).lower()) if m else
             re.sub(r'[^a-z0-9]+', '-', hh.lower()).strip('-')[:50] or 'node')
    return ('former-' + s) if former else s


SECTION = re.compile(r'^\u00a7\u00a7?\s*([0-9][0-9A-Za-z.]*(?:\s*(?:[-\u2013\u2014]|to|and|&|,)\s*[0-9][0-9A-Za-z.]*)*)')


def section_id(h):
    m = SECTION.match(h)
    if not m:
        return None
    sid = re.sub(r'\s+', '', m.group(1)).rstrip('.')
    for a in ('\u2013', '\u2014', 'to', 'and', '&', ','):
        sid = sid.replace(a, '-')
    return re.sub(r'[^0-9A-Za-z.-]', '', sid) or None


FOLDER = ('title', 'division', 'part', 'chapter', 'subchapter')


def load_tree():
    t = json.loads((CACHE / 'tree.json').read_text('utf-8'))
    nodes = {int(k): v for k, v in t['nodes'].items()}
    return nodes, t['order']


def is_folder(n, nodes, depth):
    """Folder levels: Title; a Division, or the Title's unnumbered first part ("General Provisions"); a Part
    directly under a Division; a Chapter (also "Former Chapter") anywhere above the sections."""
    k = kind(n['heading'])
    if depth == 0:
        return True
    if depth == 1:
        return True
    if k == 'part' and depth == 2:
        return True
    if k in ('chapter',) and n['kids']:
        return True
    return False


def ordinal_title(h):
    m = re.match(r'Title (\d+)', h)
    return int(m.group(1))


# ---------------------------------------------------------------------------------------------- text

def join_lines(lines, vocab):
    """Join a paragraph's lines. A line-end hyphen before a lower-case letter is a soft (typesetting) one and is
    dropped, unless the hyphenated word occurs elsewhere in the Code in the middle of a line ("long-term")."""
    text = ''
    for ln in lines:
        if not text:
            text = ln
            continue
        if text.endswith('-') and not text.endswith(' -') and not text.endswith('--'):
            left = re.search(r'([A-Za-z]+)-$', text)
            right = re.match(r'([a-z]+)', ln)
            if left and right and (left.group(1) + '-' + right.group(1)).lower() not in vocab:
                text = text[:-1] + ln
            else:
                text += ln
        else:
            text += ' ' + ln
    return re.sub(r'\s+', ' ', text).strip()


HYPH = re.compile(r'(?<![A-Za-z-])([A-Za-z]+)-([A-Za-z]+)(?![A-Za-z])')


def vocabulary(parsed):
    v = Counter()
    for r in parsed.values():
        for p in r['paras']:
            for ln in p['lines']:
                for m in HYPH.finditer(ln.rstrip('-') if ln.endswith('-') else ln):
                    v[(m.group(1) + '-' + m.group(2)).lower()] += 1
    return set(v)


def pdf_date(meta_date):
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", meta_date or '')
    if not m:
        return None
    y, mo, d = map(int, m.groups())
    if 1990 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
        return '%04d-%02d-%02d' % (y, mo, d)
    return None


def file_date(href, meta, retrieved):
    """(date, source): the upload stamp in an amended/added PDF's address, else the PDF's modDate, else its
    creationDate, else the retrieval day. A PDF date carries the producer's zone; the date part is used as printed
    (the Commission's PDFs say +10'00', Chamorro time)."""
    m = STAMPED.search(href)
    if m:
        return '%s-%s-%s' % m.groups()[:3], 'upload-stamp'
    for k, src in (('modDate', 'pdf-modified'), ('creationDate', 'pdf-created')):
        d = pdf_date(meta.get(k))
        if d:
            return d, src
    return retrieved, 'retrieved'


# ---------------------------------------------------------------------------------------------- notes

def pl_date(s):
    m = re.match(r'([A-Z][a-z]{2})[a-z]*\.?\s*(\d{1,2}),?\s*(\d{4})$', s or '')
    if not m or m.group(1).lower() not in MONTHS:
        return ''
    y, mo, d = int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))
    return '%04d-%02d-%02d' % (y, mo, d) if 1 <= d <= 31 and 1970 <= y <= 2100 else ''


def note_rows(path, sid, lines):
    """One row per public law a Source note cites: (file, section, public law, kind, date, note). `kind` is the
    last verb before the citation ("amended by PL 24-36" -> amended); `enacted` for the first law when no verb
    precedes it. The date is the one printed after it, '' when none is."""
    rows = []
    for ln in lines:
        if not re.match(r'Source\s*:', ln):
            continue
        kind_, pos = 'enacted', 0
        for m in PL.finditer(ln):
            verbs = VERB.findall(ln[pos:m.start()])
            if verbs:
                v = verbs[-1].lower().replace(' ', '')
                kind_ = 'repealed and reenacted' if v.startswith('repealed') and 'enact' in v else v.replace('-', '')
            pos = m.end()
            dm = PL_DATE.match(ln[m.end():])
            rows.append([path, sid, 'PL %d-%d' % (int(m.group(1)), int(m.group(2))), kind_,
                         pl_date(dm.group(1)) if dm else '', ln])
    return rows


def pl_key(pl):
    a, b = pl[3:].split('-')
    return int(a), int(b)


# ---------------------------------------------------------------------------------------------- git

class Writer:
    def __init__(self, repo):
        self.p = subprocess.Popen(['git', 'fast-import', '--quiet', '--done', '--force'], cwd=repo,
                                  stdin=subprocess.PIPE)
        self.mark = 0

    def w(self, b):
        self.p.stdin.write(b)

    def data(self, b):
        self.w(b'data %d\n' % len(b) + b + b'\n')

    def commit(self, author, when_, message, files):
        self.mark += 1
        self.w(b'commit refs/heads/main\nmark :%d\n' % self.mark)
        self.w(('author %s <%s> %s\n' % (author[0], author[1], when_)).encode('utf-8'))
        self.w(('committer %s <%s> %s\n' % (COMMITTER[0], COMMITTER[1], when_)).encode('utf-8'))
        self.data(message.encode('utf-8'))
        if self.mark > 1:
            self.w(b'from :%d\n' % (self.mark - 1))
        for path, content in files:
            self.w(('M 100644 inline %s\n' % path).encode('utf-8'))
            self.data(content if isinstance(content, bytes) else content.encode('utf-8'))

    def done(self):
        self.w(b'done\n')
        self.p.stdin.close()
        if self.p.wait():
            raise SystemExit('fast-import failed')


def when(day):
    y, m, d = map(int, day.split('-'))
    return '%d %s' % (calendar.timegm((y, m, d, 2, 0, 0)), TZ)  # 12:00 UTC+10 = 02:00 UTC


# ---------------------------------------------------------------------------------------------- units

def pdf_rel(href):
    return '/'.join(href.split('/')[2:])


def parsed_key(rel):
    return rel.replace('/', '__')


def load_units(today, partial):
    nodes, order = load_tree()
    log = json.loads((CACHE / 'pdfs-log.json').read_text()) if (CACHE / 'pdfs-log.json').exists() else {}
    parsed = {}
    missing = []
    for i in order:
        n = nodes[i]
        if n['pdfs']:
            rel = pdf_rel(n['pdfs'][0])
            p = PARSED / (parsed_key(rel) + '.json')
            if p.exists():
                parsed[rel] = json.loads(p.read_text('utf-8'))
            else:
                missing.append(rel)
    if missing and not partial:
        raise SystemExit(f'{len(missing)} PDFs not parsed yet (e.g. {missing[:3]}); pass --partial for a first build')
    vocab = vocabulary(parsed)
    units = {}
    unit_order = []
    taken = defaultdict(set)
    folder_of = {}
    for i in order:
        n = nodes[i]
        depth = len(n['path'])
        parent = n['path'][-1] if n['path'] else None
        if is_folder(n, nodes, depth) and not n['pdfs']:
            base = folder_of[parent] + '/' if parent is not None else ''
            s = slug(n['heading'], kind(n['heading']))
            d = base + s
            k = 2
            while d in taken[base]:
                d = f'{base}{s}-{k}'
                k += 1
            taken[base].add(d)
            folder_of[i] = d
            continue
        # not a folder: it sits in its nearest folder ancestor
        anc = [a for a in n['path'] if a in folder_of]
        fid = anc[-1]
        if not n['pdfs']:
            continue
        rel = pdf_rel(n['pdfs'][0])
        if rel not in parsed:
            continue
        u = units.get(fid)
        if u is None:
            tnode = nodes[n['path'][0]]
            u = units[fid] = {'id': fid, 'dir': folder_of[fid], 'title': ordinal_title(tnode['heading']),
                              'title_name': tnode['heading'].split(':', 1)[1].strip(),
                              'chain': [nodes[a]['heading'] for a in n['path'] if a in folder_of],
                              'node': fid, 'files': [], 'names': set(), 'emitted': set()}
            unit_order.append(fid)
        # headings between the folder and this node, not yet written
        heads = []
        below = n['path'][n['path'].index(fid) + 1:]
        for a in below:
            if a not in u['emitted']:
                u['emitted'].add(a)
                heads.append('## ' + nodes[a]['heading'])
        sid = section_id(n['heading'])
        name = sid or slug(n['heading'], kind(n['heading']))
        base, k = name, 2
        while name in u['names']:
            name = f'{base}-{k}'
            k += 1
        u['names'].add(name)
        r = parsed[rel]
        lines = [join_lines(p['lines'], vocab) for p in r['paras']]
        retrieved = log.get(SITE + n['pdfs'][0], {}).get('fetched', today)
        date, dsrc = file_date(n['pdfs'][0], r['meta'], retrieved)
        u['files'].append({'name': name, 'sid': sid, 'heading': n['heading'], 'lines': heads + lines,
                           'date': date, 'date_source': dsrc, 'pdf': rel, 'url': SITE + n['pdfs'][0],
                           'node': i, 'pages': r['pages'], 'retrieved': retrieved})
    out = [units[f] for f in unit_order]
    for u in out:
        del u['names'], u['emitted']
    return out, missing


def unit_label(u):
    """'2 CMC Div. 4, Ch. 4' and the like, from the folder chain."""
    parts = []
    for h in u['chain'][1:]:
        hh = re.sub(r'^Former\s+', 'Former ', h)
        m = re.match(r'(Former )?(Division|Part|Chapter|Subchapter)\s+([0-9]+[A-Za-z]?)', hh)
        if m:
            parts.append((m.group(1) or '') + {'Division': 'Div.', 'Part': 'Pt.', 'Chapter': 'Ch.',
                                               'Subchapter': 'Subch.'}[m.group(2)] + ' ' + m.group(3))
        else:
            parts.append(h.rstrip('.'))
    return f"{u['title']} CMC " + ', '.join(parts) if parts else f"{u['title']} CMC"


def message(u, files, day, rows):
    pls = sorted({r[2] for r in rows}, key=pl_key)
    lab = unit_label(u)
    srcs = sorted({f['date_source'] for f in files})
    n = len(files)
    def short(f):
        return '§ ' + f['sid'] if f['sid'] else f['heading'].rstrip('.')
    what = short(files[0]) if n == 1 else f'{n} sections'
    subj = f'{lab}: {what} as compiled {day}'
    if len(subj) > 120:
        subj = subj[:117].rstrip() + '...'
    body = (f"The text of {lab} ({u['chain'][-1]}) as the CNMI Law Revision Commission publishes it, "
            f"{'uploaded' if srcs == ['upload-stamp'] else 'in PDFs made'} {day}: "
            + ', '.join(short(f) for f in files[:12])
            + (', ...' if n > 12 else '') + '.\n'
            "The Commission keeps no earlier versions online, so this commit holds the whole text and no line is\n"
            "credited to a public law. The Source notes name the laws behind each section; they are listed in\n"
            f"data/amendments.csv ({len(rows)} citations of {len(pls)} public laws).")
    tr = ['Kind: consolidated', f'Consolidated: {day}', f'In-force: {day}', f'Law: {lab}',
          'Date-source: ' + ', '.join(srcs), f'Sections: {n}']
    if pls:
        tr.append(f'Latest-cited: {pls[-1]}')
    tr.append(f"Source: {SITE}/commonwealth-code/{u['node']}")
    return subj + '\n\n' + body + '\n\n' + '\n'.join(tr) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo')
    ap.add_argument('--today', required=True)
    ap.add_argument('--partial', action='store_true', help='build from the PDFs parsed so far')
    ap.add_argument('--stats', action='store_true')
    a = ap.parse_args()
    units, missing = load_units(a.today, a.partial)
    allrows = []
    for u in units:
        u['rows'] = {}
        for f in u['files']:
            rows = note_rows(f"{u['dir']}/{f['name']}.md", f['sid'] or '', f['lines'])
            u['rows'][f['name']] = rows
            allrows += rows
    nfiles = sum(len(u['files']) for u in units)
    if a.stats:
        print(len(units), 'units', nfiles, 'files', len(allrows), 'PL citations', len(missing), 'PDFs missing')
        print(Counter(f['date_source'] for u in units for f in u['files']))
        print(Counter(f['date'][:4] for u in units for f in u['files']).most_common())
        return
    late = [(u['dir'], f['name'], f['date']) for u in units for f in u['files'] if f['date'] > a.today]
    if late:
        raise SystemExit(f'{len(late)} files dated after --today {a.today}: {late[:5]}')
    repo = Path(a.repo)
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / '.git').exists():
        subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=repo, check=True)
        subprocess.run(['git', 'config', 'core.autocrlf', 'false'], cwd=repo, check=True)
    elif subprocess.run(['git', 'rev-parse', '-q', '--verify', 'refs/heads/main'], cwd=repo,
                        capture_output=True).returncode == 0:
        raise SystemExit(f'{repo} already has a main branch: build into a new, empty folder')
    # one commit per unit per day; index.txt lists the unit's files present so far, in the Code's order
    groups = defaultdict(list)
    for ui, u in enumerate(units):
        for f in u['files']:
            groups[(f['date'], ui)].append(f)
    sys.path.insert(0, str(HERE))
    import docs
    retrieved = max(f['retrieved'] for u in units for f in u['files'])
    w = Writer(repo)
    present = defaultdict(set)
    for (day, ui) in sorted(groups):
        u = units[ui]
        fs = groups[(day, ui)]
        present[ui].update(f['name'] for f in fs)
        rows = [r for f in fs for r in u['rows'][f['name']]]
        files = [(f"{u['dir']}/{f['name']}.md", '\n'.join(f['lines']) + '\n') for f in fs]
        files.append((f"{u['dir']}/index.txt",
                      ''.join(f['name'] + '.md\n' for f in u['files'] if f['name'] in present[ui])))
        w.commit(PUBLISHER, when(day), message(u, fs, day, rows), files)
    w.commit(COMMITTER, when(retrieved),
             f'Documentation: README, REPRODUCE, tools and data\n\nBuilt from the Law Revision Commission cache '
             f'retrieved up to {retrieved}.\n\nKind: documentation\nIn-force: {retrieved}\n',
             docs.files(units, allrows, retrieved, a.today, len(groups), missing))
    w.done()
    subprocess.run(['git', 'checkout', '-q', '-f', 'main'], cwd=repo, check=True)
    print('built', len(groups) + 1, 'commits;', len(units), 'units;', nfiles, 'files;', len(missing), 'PDFs missing')


if __name__ == '__main__':
    main()
