#!/usr/bin/env python3
"""Build FinMark Web and Claude variants from one source.

Usage: python3 build.py <version> [snapshot.json]
Inputs : src/app.html, data/instruments.json, data/forecasts.json,
         vendor/{d3-array.min.js,d3-geo.min.js,topojson-client.min.js,countries-110m.json}
         optional snapshot.json (a finmark-data.json) embedded as the fallback / Claude copy data
Outputs: build/FinMark-Web-v<V>.html  (upload as public_html/finmark/index.html)
         build/FinMark-Claude-v<V>.html (snapshot copy for a Claude artifact)
"""
import json, sys, pathlib

V = sys.argv[1] if len(sys.argv) > 1 else "0.0"
SNAP = sys.argv[2] if len(sys.argv) > 2 else None
root = pathlib.Path(__file__).parent
src = (root / "src/app.html").read_text()
vend = root / "vendor"
inst = json.loads((root / "data/instruments.json").read_text())
fc = json.loads((root / "data/forecasts.json").read_text())
snap = json.loads(pathlib.Path(SNAP).read_text()) if SNAP else None
SITE = "https://invisory.uk/finmark/"
J = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))


def common(s, build):
    rep = {
        "/*__BUILD__*/": f'const BUILD="{build}";',
        "/*__D3ARRAY__*/": (vend / "d3-array.min.js").read_text(),
        "/*__D3GEO__*/": (vend / "d3-geo.min.js").read_text(),
        "/*__TOPOJSON__*/": (vend / "topojson-client.min.js").read_text(),
        "/*__WORLD__*/": "const WORLD_TOPO=" + (vend / "countries-110m.json").read_text().strip(),
        "/*__INSTRUMENTS__*/": "const INSTRUMENTS=" + J(inst) + ";",
        "/*__FORECASTS__*/": "const FORECASTS=" + J(fc) + ";",
        "/*__DATA__*/": "const SNAPSHOT=" + (J(snap) if snap else "null") + ";",
    }
    for k, v in rep.items():
        assert k in s, k
        s = s.replace(k, v)
    return s


def document(s, head_extra=""):
    cut = s.index('<header class="top">')
    head, body = s[:cut], s[cut:]
    head = head.replace("<!--__HEADEXTRA__-->", head_extra)
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<style>body{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}[hidden]{display:none!important}</style>\n'
            + head.strip() + "\n</head><body>\n" + body.rstrip() + "\n</body></html>\n")


icons = ('<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png?v=1">'
         '<link rel="icon" type="image/png" sizes="16x16" href="favicon-16.png?v=1">'
         '<link rel="icon" type="image/png" sizes="192x192" href="favicon-192.png?v=1">'
         '<link rel="shortcut icon" href="favicon.ico?v=1">'
         '<link rel="apple-touch-icon" href="apple-touch-icon.png?v=1">'
         '<meta name="apple-mobile-web-app-title" content="FinMark">'
         '<meta name="theme-color" content="#0E2033">'
         '<link rel="canonical" href="' + SITE + '">'
         '<meta property="og:type" content="website"><meta property="og:site_name" content="Invisory">'
         '<meta property="og:title" content="FinMark — global markets dashboard">'
         '<meta property="og:description" content="Major and small-cap indices, currencies, futures, US yields and commodities: '
         'live quotes, adjustable date ranges, a world market map and bank forecast overlays.">'
         '<meta property="og:url" content="' + SITE + '">'
         '<meta property="og:image" content="' + SITE + 'og-image.png?v=1"><meta property="og:image:type" content="image/png">'
         '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
         '<meta property="og:image:alt" content="FinMark: world map of market moves with index tiles">'
         '<meta name="twitter:card" content="summary_large_image">'
         '<meta name="twitter:image" content="' + SITE + 'og-image.png?v=1">')

out = root / "build"; out.mkdir(exist_ok=True)
web = document(common(src, "web"), icons)
cl = document(common(src, "claude"))
(out / f"FinMark-Web-v{V}.html").write_text(web)
(out / f"FinMark-Claude-v{V}.html").write_text(cl)
for f in (f"FinMark-Web-v{V}.html", f"FinMark-Claude-v{V}.html"):
    print(f, (out / f).stat().st_size)
