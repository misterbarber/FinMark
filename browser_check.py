import sys, asyncio
from playwright.async_api import async_playwright
F=sys.argv[1]; tag=sys.argv[2]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox"])
        for (w,h,scheme) in [(1360,900,"light"),(390,844,"dark")]:
            pg=await b.new_page(viewport={"width":w,"height":h},color_scheme=scheme)
            errs=[]; pg.on("pageerror",lambda e:errs.append(str(e))); pg.on("console",lambda m:m.type=="error" and errs.append("console: "+m.text[:160]))
            await pg.route("**/*", lambda r: r.abort() if any(x in r.request.url for x in ("githubusercontent","tradingview")) else r.continue_())
            await pg.goto("file://"+F); await pg.wait_for_timeout(1200)
            for v in ["dashboard","markets","chart","map","forecasts","method"]:
                await pg.click(f'.tab[data-v="{v}"]'); await pg.wait_for_timeout(500)
                await pg.screenshot(path=f"/home/claude/finmark/test/shots/{tag}-{w}-{v}.png",full_page=(v!="chart" or w<500))
            sw=await pg.evaluate("document.documentElement.scrollWidth"); print(tag,w,"scrollWidth",sw,"errors",errs[:5])
            await pg.close()
        await b.close()
asyncio.run(main())
