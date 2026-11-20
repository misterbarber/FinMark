# Renders FinMark browser icons and the link-preview card with headless Chrome.
import asyncio, pathlib, re
from playwright.async_api import async_playwright
from PIL import Image
R=pathlib.Path(__file__).resolve().parent.parent; SITE=R/"site"
app=(R/"src/app.html").read_text()
ICON=re.search(r'<svg viewBox="0 0 64 64".*?</svg>',app,re.S).group(0)
V=R/"vendor"
OG=f"""<!DOCTYPE html><html><head><style>
body{{margin:0;width:1200px;height:630px;background:#0E2033;color:#F4F7F9;font-family:'IBM Plex Sans',Arial,sans-serif;overflow:hidden;position:relative}}
#m{{position:absolute;right:-40px;top:70px;width:900px;height:470px}}
.t{{position:absolute;left:70px;top:150px;z-index:2}}
.t svg{{width:120px;height:120px}}
h1{{font-family:'Barlow Condensed','Arial Narrow',Arial,sans-serif;font-size:118px;letter-spacing:.06em;margin:18px 0 0;line-height:1;text-transform:uppercase}}
p{{font-size:30px;margin:14px 0 0;opacity:.85;max-width:560px;line-height:1.3}}
.b{{position:absolute;left:70px;bottom:52px;font-size:22px;color:#D7AE55;letter-spacing:.04em}}
</style><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700&family=IBM+Plex+Sans:wght@400&display=swap"></head><body>
<svg id="m"></svg><div class="t">{ICON}<h1>FinMark</h1><p>Global indices, currencies, futures and commodities on one live dashboard</p></div><div class="b">invisory.uk/finmark</div>
<script>{(V/'d3-array.min.js').read_text()}</script><script>{(V/'d3-geo.min.js').read_text()}</script><script>{(V/'topojson-client.min.js').read_text()}</script>
<script>const T={(V/'countries-110m.json').read_text()};const f=topojson.feature(T,T.objects.countries).features.filter(x=>x.id!=="010");
const lit=new Set(["840","124","484","076","032","826","276","250","724","380","528","756","752","392","156","158","410","356","036","554","360","682","376","792"]);
const p=d3.geoNaturalEarth1().fitSize([900,470],{{type:"FeatureCollection",features:f}}),g=d3.geoPath(p);
document.getElementById("m").innerHTML=f.map(x=>'<path d="'+g(x)+'" fill="'+(lit.has(x.id)?"#0D7471":"#1B3550")+'" stroke="#0E2033" stroke-width=".6"/>').join("");</script></body></html>"""
async def main():
    async with async_playwright() as pw:
        b=await pw.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox"])
        for n,s in [("favicon-16.png",16),("favicon-32.png",32),("favicon-192.png",192),("apple-touch-icon.png",180),("icon-512.png",512)]:
            pg=await b.new_page(viewport={"width":s,"height":s},device_scale_factor=1)
            await pg.set_content(f'<html><body style="margin:0;background:transparent">{ICON.replace("<svg ",f"<svg width={s} height={s} ")}</body></html>')
            await pg.screenshot(path=str(SITE/n),omit_background=True); await pg.close()
        pg=await b.new_page(viewport={"width":1200,"height":630}); await pg.set_content(OG); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=str(SITE/"og-image.png")); await b.close()
    Image.open(SITE/"icon-512.png").save(SITE/"favicon.ico",sizes=[(16,16),(32,32),(48,48),(64,64)])
    (SITE/"icon-512.png").unlink()
asyncio.run(main()); print(sorted(p.name for p in SITE.iterdir()))
