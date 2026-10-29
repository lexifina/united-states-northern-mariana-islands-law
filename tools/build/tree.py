"""The Commonwealth Code's tree, read from the cached node pages (fetch.py pages).

    python tree.py            -> .cache/tree.json, and prints the level chains with counts

Each node page (/commonwealth-code/<id>) has a breadcrumb of its ancestors, an <h3> heading, and either a list of
its children in the Code's order (<ul class="codelist">) or one PDF (a section, or a chapter/article/form printed
whole). The tree is walked from the Titles listed on the Code's index page, children in page order.
"""
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
CACHE = HERE / '.cache'
NODE = re.compile(r'<a href="https://cnmilaw\.gov/commonwealth-code/(\d+)">(.*?)</a>', re.S)


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def read_node(i):
    s = (CACHE / 'node' / f'{i}.html').read_text('utf-8', errors='replace')
    a = s.find('class="crumbs"')
    b = s.find('</main>', a)
    body = s[a:b]
    crumbs = s[a:s.find('</p>', a)]
    h = re.search(r'<h3>(.*?)</h3>', body, re.S)
    kids = []
    ul = re.search(r'<ul class="codelist">(.*?)</ul>', body, re.S)
    if ul:
        kids = [int(k) for k, _ in NODE.findall(ul.group(1))]
    pdfs = []
    for p in re.findall(r'href="(/docs/[^"]+\.pdf)"', body):
        if p not in pdfs:
            pdfs.append(p)
    return {'id': i, 'heading': clean(h.group(1)) if h else '', 'crumbs': [int(k) for k, _ in NODE.findall(crumbs)],
            'kids': kids, 'pdfs': pdfs}


def titles():
    s = (CACHE / 'node' / 'root.html').read_text('utf-8', errors='replace')
    out = []
    for k, label in re.findall(r'<a [^>]*href="(?:https://cnmilaw\.gov)?/commonwealth-code/(\d+)"[^>]*>(.*?)</a>', s, re.S):
        if re.match(r'Title \d+', clean(label)) and int(k) not in out:
            out.append(int(k))
    if not out:  # the tree is drawn by script: take the Titles from the sitemap's nodes instead
        raise SystemExit('no Titles found on the index page')
    return out


def kind(heading):
    m = re.match(r'(Title|Division|Part|Chapter|Subchapter|Article|Subarticle|Section|Forms?|Appendix|Schedule)\b',
                 heading, re.I)
    if m:
        return m.group(1).lower().rstrip('s') if m.group(1).lower() == 'forms' else m.group(1).lower()
    if heading.startswith('§'):
        return 'section'
    if re.match(r'[A-Z]\.\s', heading):
        return 'letter'
    return 'other'


def load():
    nodes = {}
    order = []

    def walk(i, path):
        if i in nodes:
            raise SystemExit(f'node {i} reached twice')
        n = read_node(i)
        n['path'] = path
        nodes[i] = n
        order.append(i)
        for k in n['kids']:
            walk(k, path + [i])

    for t in titles():
        walk(t, [])
    return nodes, order


def main():
    sys.setrecursionlimit(10000)
    nodes, order = load()
    (CACHE / 'tree.json').write_text(json.dumps({'order': order, 'nodes': {str(k): v for k, v in nodes.items()}},
                                                ensure_ascii=False), encoding='utf-8', newline='\n')
    sm = (CACHE / 'sitemap-code.xml').read_text('utf-8')
    ids = {int(x) for x in re.findall(r'/commonwealth-code/(\d+)</loc>', sm)}
    print(len(nodes), 'nodes reached;', len(ids - set(nodes)), 'sitemap nodes not reached:', sorted(ids - set(nodes))[:20])
    chains = Counter()
    for i in order:
        n = nodes[i]
        if n['pdfs'] or not n['kids']:
            chains['/'.join(kind(nodes[p]['heading']) for p in n['path']) + ' > ' + kind(n['heading']) +
                   ('' if n['pdfs'] else ' (empty)')] += 1
    for c, v in chains.most_common():
        print(v, c)


if __name__ == '__main__':
    main()
