"""Print a chapter of the Commonwealth Code of the Northern Mariana Islands, or one section of it, as this repository
has it on a date.

    python tools/in_force_on.py 2026-10-29 "1 CMC 101"                                   # by citation
    python tools/in_force_on.py 2026-10-29 title-01/general-provisions/chapter-01 101     # by folder and section
    python tools/in_force_on.py 2026-10-29 title-01/general-provisions/chapter-01         # the whole chapter, in order
    python tools/in_force_on.py 2026-10-29 title-02                                       # every chapter of a title

Reads the `In-force:` trailer, which holds the day the Law Revision Commission made the section's PDF. The
Commission keeps only the current text, so a date before that day has no version here. Standard library only.
"""
import re
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(['git', '-c', 'core.quotepath=false', *args], capture_output=True, text=True,
                          encoding='utf-8', check=True).stdout


def by_citation(cite: str) -> tuple[str, str] | None:
    """'1 CMC 101', '1 CMC § 101', '4 CMC § 1104' -> (folder, section), found in main's tree."""
    m = re.fullmatch(r'\s*(\d+)\s*C\.?M\.?C\.?\s*(?:§+|[Ss]ec(?:tion|\.)?)?\s*([0-9][0-9A-Za-z.]*)\s*', cite)
    if not m:
        return None
    want = m.group(2).rstrip('.')
    for path in git('ls-tree', '-r', '--name-only', 'main', 'title-%02d/' % int(m.group(1))).splitlines():
        folder, _, name = path.rpartition('/')
        if name == want + '.md':
            return folder, want
    return None


def commit_on(day: str, path: str) -> tuple[str | None, str | None]:
    """The last commit on or before `day` that touched `path`, and the earliest date known for it."""
    fmt = '%H%x1f%(trailers:key=In-force,valueonly,separator=)'
    earliest = None
    for line in git('log', '--first-parent', f'--format={fmt}', 'main', '--', path).splitlines():
        h, d = (line.split('\x1f') + [''])[:2]
        d = d.strip()
        if not d:
            continue
        earliest = d
        if d <= day:
            return h, d
    return None, earliest


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    day = sys.argv[1]
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        sys.exit(f'{day}: give the date as YYYY-MM-DD')
    if 'CMC' in sys.argv[2].upper().replace('.', ''):
        found = by_citation(sys.argv[2])
        if not found:
            sys.exit(f'{sys.argv[2]}: no such section in this repository')
        law, unit = found
    else:
        law = sys.argv[2].strip('/')
        unit = sys.argv[3] if len(sys.argv) > 3 else None
    if unit and unit.endswith('.md'):
        unit = unit[:-3]
    if unit:
        path = f'{law}/{unit}.md'
        h, earliest = commit_on(day, path)
        if not h:
            if earliest:
                sys.exit(f'{path}: no version on or before {day}; the record starts at {earliest}, the date of the '
                         'earliest PDF of it the Law Revision Commission has online')
            sys.exit(f'{path}: not found')
        sys.stdout.write(git('show', f'{h}:{path}'))
        return
    # a whole chapter (or every chapter under a title, division or part): each file as it stood on the day, in the
    # Code's order (each chapter's index.txt at main)
    indexes = [p for p in git('ls-tree', '-r', '--name-only', 'main', law + '/').splitlines()
               if p.endswith('/index.txt')]
    if not indexes:
        sys.exit(f'{law}: not found')
    # one pass over the folder's history: for each file, the newest commit on or before the day that touched it
    latest: dict[str, str] = {}
    h = None
    for line in git('log', '--first-parent', '--name-only',
                    '--format=\x1e%H%x1f%(trailers:key=In-force,valueonly,separator=)', 'main', '--', law).split('\n'):  # not splitlines(): it breaks at \x1e
        if line.startswith('\x1e'):
            h, d = (line[1:].split('\x1f') + [''])[:2]
            h = h if d.strip() and d.strip() <= day else None
        elif line and h and line not in latest:
            latest[line] = h
    shown = 0
    for ix in indexes:
        folder = ix.rsplit('/', 1)[0]
        for n in [n for n in git('show', f'main:{ix}').splitlines() if n]:
            h = latest.get(f'{folder}/{n}')
            if h:
                sys.stdout.write(git('show', f'{h}:{folder}/{n}') + '\n')
                shown += 1
    if not shown:
        sys.exit(f'{law}: no section has a version on or before {day}')


if __name__ == '__main__':
    main()
