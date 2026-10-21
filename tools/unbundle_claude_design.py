#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Desempaqueta un export «bundle» de Claude Design (un solo HTML autocontenido, con
los activos en base64 dentro de un manifest) a HTML estático + carpeta assets/.

Uso:
    python tools/unbundle_claude_design.py <bundle.html> <dir_salida>

Resultado:
    <dir_salida>/index.html
    <dir_salida>/assets/js/…      runtime, componentes, React y ReactDOM
    <dir_salida>/assets/fonts/…   woff2 por familia, peso y subconjunto
    <dir_salida>/assets/img/…     imágenes del manifest y las que iban inline en base64

El HTML resultante es la plantilla del bundle con las referencias a UUID y a
data: URIs sustituidas por rutas relativas, más el <script> con window.__resources
que el runtime usa para cargar React desde archivos locales en vez de unpkg.
No cambia nada más: ni textos, ni estilos, ni scripts.

Los nombres de archivo llevan un hash corto del contenido (cache busting), salvo
las librerías versionadas (react-18.3.1.min.js). Los activos que nada referencia
se omiten y se listan al final.
"""
import base64
import gzip
import hashlib
import json
import os
import re
import sys
import unicodedata
from urllib.parse import urlparse

MIME_EXT = {
    'image/webp': 'webp', 'image/jpeg': 'jpg', 'image/png': 'png', 'image/gif': 'gif',
    'image/svg+xml': 'svg', 'image/avif': 'avif',
    'font/woff2': 'woff2', 'font/woff': 'woff', 'font/ttf': 'ttf',
    'application/javascript': 'js', 'text/javascript': 'js', 'text/css': 'css',
    'application/json': 'json',
}
UUID_RE = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'


def block(html, name, required=True):
    m = re.search(r'<script type="__bundler/%s">\s*(.*?)\s*</script>' % re.escape(name), html, re.S)
    if not m:
        if required:
            sys.exit(f'No se encontró el bloque __bundler/{name}: ¿es un export bundle de Claude Design?')
        return None
    return m.group(1)


def slug(s, maxlen=48):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    if len(s) > maxlen:
        cut = s.rfind('-', 0, maxlen + 1)
        s = s[:cut if cut > maxlen // 2 else maxlen]
    return s.strip('-') or 'sin-nombre'


def h8(data):
    return hashlib.sha1(data).hexdigest()[:8]


def main(src, out):
    html = open(src, encoding='utf-8').read()
    manifest = json.loads(block(html, 'manifest'))
    ext = json.loads(block(html, 'ext_resources'))
    template = json.loads(block(html, 'template'))
    page_order_raw = block(html, 'page_order', required=False)
    if page_order_raw and json.loads(page_order_raw):
        sys.exit('El bundle tiene páginas anidadas (iframes): este script no las soporta.')
    ext_by_uuid = {e['uuid']: e['id'] for e in ext}

    # ---- decodificar activos ----
    assets = {}
    for uuid, e in manifest.items():
        raw = base64.b64decode(e['data'])
        data = gzip.decompress(raw) if e.get('compressed') else raw
        assets[uuid] = {'mime': e['mime'], 'data': data, 'ext': MIME_EXT.get(e['mime'], 'bin'),
                        'name': None, 'sub': None, 'hashed': True}

    # ---- nombres por contexto ----
    # 1) librerías externas (React, ReactDOM…): paquete-versión de la URL original
    for uuid, url in ext_by_uuid.items():
        if uuid not in assets:
            continue
        p = urlparse(url)
        base = os.path.basename(p.path)
        m = re.search(r'/((?:@[^/]+/)?[^/@]+)@([^/]+)/', p.path)
        pkg_ver = f'{slug(m.group(1))}-{m.group(2)}' if m else slug(os.path.splitext(base)[0])
        name = f'{pkg_ver}.min' if base.endswith('.min.js') else pkg_ver
        assets[uuid].update(sub='js', name=name, hashed=False)

    # 2) scripts referenciados por la plantilla
    for uuid in re.findall(r'<script[^>]+src="(%s)"' % UUID_RE, template):
        if uuid in assets and not assets[uuid]['name']:
            txt = assets[uuid]['data'].decode('utf-8', 'replace')
            if 'dc-runtime' in txt:
                name = 'dc-runtime'
            elif 'image-slot' in txt:
                name = 'dc-components'
            else:
                name = 'script'
            assets[uuid].update(sub='js', name=name)

    # 3) fuentes: /* subconjunto */ @font-face { font-family:'X'; font-weight:W; src:url("uuid") }
    faces = {}
    for subset, body in re.findall(r'/\*\s*([a-z-]+)\s*\*/\s*@font-face\s*\{(.*?)\}', template, re.S):
        fam = re.search(r"font-family:\s*'([^']+)'", body)
        w = re.search(r'font-weight:\s*([^;]+);', body)
        u = re.search(r'url\("(%s)"\)' % UUID_RE, body)
        if not (fam and u):
            continue
        f = faces.setdefault(u.group(1), {'fam': fam.group(1), 'subsets': set(), 'weights': set()})
        f['subsets'].add(subset)
        if w:
            f['weights'].add(w.group(1).strip())
    for uuid, f in faces.items():
        if uuid in assets and not assets[uuid]['name']:
            ws = sorted(f['weights'], key=lambda x: int(re.sub(r'\D', '', x) or 0))
            wpart = ws[0] if len(ws) == 1 else (f'{ws[0]}-{ws[-1]}' if ws else 'var')
            assets[uuid].update(sub='fonts', name=f"{slug(f['fam'])}-{wpart}-{'-'.join(sorted(f['subsets']))}")

    # 4) <image-slot id="logo" … src="uuid">
    for tag in re.findall(r'<image-slot[^>]*>', template):
        idm = re.search(r'\bid="([^"{}]+)"', tag)
        sm = re.search(r'\bsrc="(%s)"' % UUID_RE, tag)
        if idm and sm and sm.group(1) in assets and not assets[sm.group(1)]['name']:
            assets[sm.group(1)].update(sub='img', name=slug(idm.group(1)))

    # 5) referencias dentro del script del componente: lista = [ { name:'…', imgId:'uuid' } ]
    for uuid, a in assets.items():
        if a['name']:
            continue
        for m in re.finditer(re.escape(uuid), template):
            start = template.rfind('{', 0, m.start())
            end = template.find('}', m.end())
            if start < 0 or end < 0:
                continue
            nm = re.search(r"\bname:\s*'([^']*)'", template[start:end + 1])
            if not nm:
                continue
            arr = re.findall(r'\b(\w+)\s*=\s*\[', template[:start])
            prefix = slug(arr[-1]) + '-' if arr else ''
            a.update(sub='img', name=prefix + slug(nm.group(1)))
            break

    # 6) resto: por tipo
    for uuid, a in assets.items():
        if not a['name']:
            a['sub'] = ('img' if a['mime'].startswith('image/') else
                        'fonts' if a['mime'].startswith('font/') else
                        'js' if a['ext'] == 'js' else 'misc')
            a['name'] = {'img': 'imagen', 'fonts': 'fuente', 'js': 'script', 'misc': 'archivo'}[a['sub']]

    # ---- huérfanos: ni en la plantilla ni en ext_resources ----
    orphans = [u for u in assets if u not in ext_by_uuid and u not in template]

    # ---- escribir activos ----
    written = []
    taken = set()
    path_by_uuid = {}

    def unique_path(sub, base, ext, data, hashed=True):
        tag = f'.{h8(data)}' if hashed else ''
        fn = f'{base}{tag}.{ext}'
        n = 2
        while fn in taken:
            fn = f'{base}-{n}{tag}.{ext}'
            n += 1
        taken.add(fn)
        return f'assets/{sub}/{fn}'

    def write(rel, data, origin):
        full = os.path.join(out, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'wb') as fh:
            fh.write(data)
        written.append((rel, len(data), origin))

    for uuid, a in assets.items():
        if uuid in orphans:
            continue
        rel = unique_path(a['sub'], a['name'], a['ext'], a['data'], a['hashed'])
        write(rel, a['data'], 'manifest')
        path_by_uuid[uuid] = rel

    # ---- data: URIs inline en la plantilla (p. ej. fotos del carrusel) ----
    tpl = template
    counters = {}

    def repl_data(m):
        tag_start = tpl.rfind('<', 0, m.start())
        tag = tpl[tag_start:m.start()]
        mime, b64 = m.group(1), m.group(2)
        data = base64.b64decode(b64)
        alt = re.search(r'\balt="([^"]+)"', tag)
        cls = re.search(r'\bclass="([^"]+)"', tag)
        if alt:
            base = slug(alt.group(1))
        elif cls:
            base = slug(re.sub(r'^fjt-|-slide$', '', cls.group(1).split()[0]))
        else:
            base = 'inline'
        counters[base] = counters.get(base, 0) + 1
        rel = unique_path('img', f'{base}-{counters[base]}', MIME_EXT.get(mime, 'bin'), data)
        write(rel, data, 'inline')
        return rel

    page = re.sub(r'data:(image/[a-z+]+);base64,([A-Za-z0-9+/=]+)', repl_data, tpl)

    # ---- sustituir UUIDs por rutas ----
    for uuid, rel in path_by_uuid.items():
        page = page.replace(uuid, rel)

    # Igual que el cargador del bundle: sin integrity/crossorigin (los bytes son locales).
    page = re.sub(r'\s+integrity="[^"]*"', '', page, flags=re.I)
    page = re.sub(r'\s+crossorigin="[^"]*"', '', page, flags=re.I)

    # window.__resources: URL original de la librería -> archivo local (lo lee el runtime)
    resource_map = {url: path_by_uuid[u] for u, url in ext_by_uuid.items() if u in path_by_uuid}
    res_script = '<script>window.__resources = ' + json.dumps(resource_map).replace('</', '<\\/') + ';</script>'
    head = re.search(r'<head[^>]*>', page, re.I)
    if not head:
        sys.exit('La plantilla no tiene <head>.')
    # Después de <meta charset> si existe (debe ir al principio del <head>); si no, tras <head>.
    charset = re.compile(r'<meta\s+charset="[^"]*"\s*/?>', re.I).search(page, head.end())
    at = charset.end() if charset and charset.start() < head.end() + 200 else head.end()
    page = page[:at] + '\n' + res_script + page[at:]

    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'index.html'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(page)

    # ---- informe ----
    leftover = sorted(set(re.findall(UUID_RE, page)))
    print(f'index.html: {len(page.encode("utf-8"))} bytes')
    by_sub = {}
    for rel, n, origin in sorted(written):
        print(f'  {n:8}  {rel}  ({origin})')
        sub = rel.split('/')[1]
        by_sub[sub] = by_sub.get(sub, 0) + n
    for sub, n in sorted(by_sub.items()):
        print(f'assets/{sub}: {n} bytes')
    print(f'total activos: {sum(by_sub.values())} bytes en {len(written)} archivos')
    if orphans:
        print('omitidos (sin referencias):')
        for u in orphans:
            a = assets[u]
            print(f'  {u}  {a["mime"]}  {len(a["data"])} bytes')
    if leftover:
        print('ATENCIÓN: quedan UUID sin sustituir en index.html:', leftover)
        sys.exit(2)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
