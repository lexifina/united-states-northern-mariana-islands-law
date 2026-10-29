"""README, REPRODUCE.md, SOURCES.md, LICENSE, corpus.json, data/ and tools for the Northern Mariana Islands law
repository (called by build.py as `docs.files(units, rows, retrieved, today, law_commits, missing)`; returns
[(path, bytes)])."""
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
REPO_FILES = HERE / 'repo'
CACHE = HERE / '.cache'
BUILD_FILES = ('fetch.py', 'tree.py', 'parse.py', 'build.py', 'docs.py', 'check_words.py')
TEMPLATES = ('README.md', 'REPRODUCE.md', 'SOURCES.md', 'LICENSE')

# A section is cited "<title> CMC § <number>"; the number is unique within its title, so the folder is the title.
CITATION = {
    'file': r'(title-[0-9]+)/.*/([0-9][0-9A-Za-z.]*)\.md',
    # whole-character alternatives only: git grep may run in a byte locale, where "§?" would make only the
    # last byte of the section sign optional
    'cites': '(§§ ?|§ ?|[Ss]ection ){n}([^0-9A-Za-z.]|[.]([^0-9]|$)|$)',
    'note': 'files are <title folder>/<division>/[<part>/]<chapter>/<section>.md; section numbers are unique within '
            'a title (1 CMC § 101 is title-01/general-provisions/chapter-01/101.md).',
}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _csv(rows: list[list]) -> bytes:
    out = io.StringIO()
    w = csv.writer(out, lineterminator='\n')
    for r in rows:
        w.writerow(r)
    return out.getvalue().encode('utf-8')


def source_sums(units) -> str:
    paths = [CACHE / 'sitemap-code.xml'] + sorted(CACHE / 'pdf' / f['pdf'] for u in units for f in u['files'])
    return ''.join(f'{p.relative_to(CACHE).as_posix()}\t{_sha(p)}\n' for p in paths)


def _pl_key(pl: str) -> tuple:
    a, b = pl[3:].split('-')
    return int(a), int(b)


def files(units, rows, retrieved, today, law_commits, missing):
    fl = [f for u in units for f in u['files']]
    days = sorted(f['date'] for f in fl)
    src = Counter(f['date_source'] for f in fl)
    laws = sorted({r[2] for r in rows}, key=_pl_key)
    stats = {
        'today': today, 'retrieved': retrieved,
        'units': len(units), 'titles': len({u['title'] for u in units}), 'sections': sum(1 for f in fl if f['sid']),
        'files': len(fl), 'whole': sum(1 for f in fl if not f['sid']),
        'commits': law_commits + 1, 'consolidated': law_commits, 'amendment': 0, 'unexplained': 0,
        'first': days[0], 'last': days[-1],
        'upload_stamped': src.get('upload-stamp', 0), 'pdf_modified': src.get('pdf-modified', 0),
        'pdf_created': src.get('pdf-created', 0), 'retrieved_dated': src.get('retrieved', 0),
        'pages': sum(f['pages'] for f in fl), 'missing_pdfs': len(missing),
        'citations': len(rows), 'public_laws': len(laws), 'dated_citations': sum(1 for r in rows if r[4]),
        'latest_cited': laws[-1] if laws else '',
        'compiled_by_year': dict(sorted(Counter(d[:4] for d in days).items())),
    }

    def fill(text: str) -> str:
        for k, v in stats.items():
            if isinstance(v, (str, int)):
                text = text.replace('{{' + k.upper() + '}}', f'{v:,}' if isinstance(v, int) else v)
        for name in BUILD_FILES:
            text = text.replace('{{SHA_' + name.upper().replace('.', '_') + '}}', _sha(HERE / name))
        if '{{' in text:
            raise SystemExit('unfilled placeholder: ' + text[text.index('{{'):text.index('{{') + 40])
        return text

    units_csv = _csv([['path', 'title', 'title_name', 'heading', 'files', 'first_compiled', 'last_compiled',
                       'citations', 'source_url']] +
                     [[u['dir'] + '/', u['title'], u['title_name'], u['chain'][-1], len(u['files']),
                       min(f['date'] for f in u['files']), max(f['date'] for f in u['files']),
                       sum(len(v) for v in u['rows'].values()), f"https://cnmilaw.gov/commonwealth-code/{u['node']}"]
                      for u in units])
    files_csv = _csv([['file', 'heading', 'compiled', 'date_source', 'pages', 'pdf', 'node_url']] +
                     [[f"{u['dir']}/{f['name']}.md", f['heading'], f['date'], f['date_source'], f['pages'],
                       f['url'], f"https://cnmilaw.gov/commonwealth-code/{f['node']}"] for u in units for f in u['files']])
    amend_csv = _csv([['file', 'section', 'public_law', 'kind', 'date', 'note']] + rows)

    corpus = {
        'corpus': 'us/northern-mariana-islands/acts',
        'parent': 'us/federal/usc',
        'name': 'Commonwealth Code of the Northern Mariana Islands (as published by the CNMI Law Revision Commission)',
        'label': 'Northern Mariana Islands',
        'language': 'en',
        'history': 'current-only',
        'history_from': days[0],
        'record_to': days[-1],
        'checked_on': retrieved,
        'record_note': 'The Law Revision Commission publishes only the current text of each section of the '
                       'Commonwealth Code, one PDF per section, and keeps no dated earlier versions, so each section '
                       'has one version here, dated by when the Commission made its PDF (the upload time for '
                       'sections it amended or added, otherwise the PDF\'s modification date). That is a compilation '
                       'date, not the day a law took effect. The Source notes naming each public law are kept as '
                       'text and listed in data/amendments.csv.',
        'built': today,
        'baseline_trailer': 'Consolidated',
        'in_force_trailer': 'In-force',
        'dates': {'commit': "the day the Commission made the section's PDF: the upload stamp in the address of an "
                            'amended or added section, else the PDF modDate, else its creationDate, else the '
                            'retrieval day',
                  'baseline_trailer': 'Consolidated', 'other_trailers': ['Date-source'],
                  'time': '12:00 UTC+10 (Chamorro Standard Time, no daylight saving time)'},
        'author': {'consolidated': 'CNMI Law Revision Commission', 'amendment': 'none yet',
                   'unexplained': 'CNMI Law Revision Commission'},
        'scope': {
            'trailer': 'Applies',
            'when_absent': 'not extracted; effective dates and savings clauses are in the public laws and, where '
                           'the Commission kept them, in the Commission Comment under each section',
            'default_reach': {
                'rule': 'presumption against retroactivity',
                'meaning': 'a statute operates prospectively unless the legislature clearly says otherwise',
                'authority': 'general rule of statutory construction applied by the CNMI courts',
                'decided_here': False,
            },
        },
        'reuse': 'Statute text is not copyrightable: under the government edicts doctrine (Georgia v. '
                 'Public.Resource.Org, Inc., 590 U.S. 255 (2020)) nobody owns works made by legislators or judges '
                 'in their official capacity, and the Commission is the Legislature\'s and courts\' own agent for '
                 'the Code (1 CMC §§ 3801-3810). Private repository; see SOURCES.md.',
        'citation': CITATION,
        'has_future_branch': False,
        'tool': 'tools/in_force_on.py',
    }
    out = {
        'corpus.json': (json.dumps(corpus, indent=2, ensure_ascii=False) + '\n').encode('utf-8'),
        'data/amendments.csv': amend_csv,
        'data/units.csv': units_csv,
        'data/files.csv': files_csv,
        'data/stats.json': (json.dumps(stats, indent=1, sort_keys=True) + '\n').encode('utf-8'),
        'data/source-sha256.tsv': source_sums(units).encode('utf-8'),
        'tools/in_force_on.py': (REPO_FILES / 'tools' / 'in_force_on.py').read_bytes(),
    }
    for name in TEMPLATES:
        out[name] = fill((REPO_FILES / name).read_text('utf-8')).encode('utf-8')
    for name in BUILD_FILES:
        if (HERE / name).exists():
            out[f'tools/build/{name}'] = (HERE / name).read_bytes()
    for name in TEMPLATES:
        out[f'tools/build/repo/{name}'] = (REPO_FILES / name).read_bytes()
    out['tools/build/repo/tools/in_force_on.py'] = (REPO_FILES / 'tools' / 'in_force_on.py').read_bytes()
    for k, v in out.items():
        if b'\r' in v:
            raise SystemExit(f'{k}: carriage return in a generated file')
    return sorted(out.items())
