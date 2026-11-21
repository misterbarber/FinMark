#!/usr/bin/env python3
"""FinMark data job: writes data/finmark-data.json for the FinMark web app.

Usage:
  python fetch_data.py full     # rebuild 10 years of history (run once a day)
  python fetch_data.py quotes   # update latest prices only (run every 15 minutes)

Prices come from Yahoo Finance through the yfinance library (delayed, personal use).
History: daily closes for the last 3 years, weekly closes before that, back to 10 years.
"""
import json, sys, time, datetime as dt, pathlib, math
import pandas as pd
import yfinance as yf

ROOT = pathlib.Path(__file__).resolve().parent.parent
INST = json.loads((ROOT / "data/instruments.json").read_text())["instruments"]
OUT = ROOT / "data/finmark-data.json"
DAILY_YEARS = 3
EPOCH = dt.date(1970, 1, 1)


def dnum(d):
    return (d - EPOCH).days


def rnd(x):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    a = abs(x)
    if a >= 1000: return round(x, 1)
    if a >= 10: return round(x, 3)
    return round(x, 5)


def download(tickers, **kw):
    """Batch download with one retry; returns {ticker: DataFrame}."""
    out = {}
    for attempt in range(2):
        try:
            df = yf.download(tickers, group_by="ticker", auto_adjust=False, progress=False, threads=True, **kw)
            break
        except Exception as e:
            print("download failed:", e); time.sleep(20); df = None
    if df is None or df.empty:
        return out
    for t in tickers:
        try:
            sub = df[t] if isinstance(df.columns, pd.MultiIndex) else df
            sub = sub.dropna(subset=["Close"])
            if not sub.empty:
                out[t] = sub
        except KeyError:
            pass
    return out


def resolve(inst, frames, **kw):
    """Primary symbol first, then fallbacks one at a time."""
    for sym in inst["yahoo"]:
        if sym in frames:
            return sym, frames[sym]
    for sym in inst["yahoo"][1:]:
        f = download([sym], **kw)
        if sym in f:
            return sym, f[sym]
    return None, None


def compress(points):
    """points: sorted list of (date, close). Daily for the last DAILY_YEARS, weekly (last close of ISO week) before."""
    if not points:
        return None
    cut = points[-1][0] - dt.timedelta(days=365 * DAILY_YEARS)
    weekly, daily, seen = [], [], {}
    for d, v in points:
        if d >= cut:
            daily.append((d, v))
        else:
            seen[d.isocalendar()[:2]] = (d, v)  # keeps last close of each week
    weekly = sorted(seen.values())
    return encode(weekly + daily)


def encode(pts):
    days = [dnum(d) for d, _ in pts]
    return {"t0": days[0], "dt": [b - a for a, b in zip(days, days[1:])], "v": [rnd(v) for _, v in pts]}


def decode(s):
    days, d = [s["t0"]], s["t0"]
    for x in s["dt"]:
        d += x; days.append(d)
    return [(EPOCH + dt.timedelta(days=k), v) for k, v in zip(days, s["v"])]


def load():
    try:
        return json.loads(OUT.read_text())
    except Exception:
        return {"schema": 1, "q": {}, "s": {}, "missing": []}


def save(doc):
    doc["generated"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False))
    print("wrote", OUT, OUT.stat().st_size, "bytes;", len(doc["q"]), "quotes;", "missing:", doc.get("missing"))


def quote_from(points, stamp=None):
    (d1, v1) = points[-1]
    v0 = points[-2][1] if len(points) > 1 else None
    return {"p": rnd(v1), "pc": rnd(v0), "d": d1.isoformat(), "ts": stamp or (d1.isoformat() + "T00:00:00Z")}


def full():
    doc = load()
    syms = [i["yahoo"][0] for i in INST]
    frames = download(syms, period="10y", interval="1d")
    missing = []
    for inst in INST:
        sym, f = resolve(inst, frames, period="10y", interval="1d")
        if f is None:
            missing.append(inst["id"]); continue
        pts = [(ix.date(), float(c)) for ix, c in f["Close"].items()]
        doc["s"][inst["id"]] = compress(pts)
        old = doc["q"].get(inst["id"], {})
        q = quote_from(pts)
        if old.get("d") == q["d"]: q["ts"] = old.get("ts", q["ts"])
        q["sym"] = sym
        doc["q"][inst["id"]] = q
    doc["missing"] = missing
    doc["mode"] = "full"
    save(doc)


def quotes():
    doc = load()
    if not doc["s"]:
        return full()
    idmap = {}
    for inst in INST:
        sym = doc["q"].get(inst["id"], {}).get("sym") or inst["yahoo"][0]
        idmap[sym] = inst["id"]
    syms = list(idmap)
    daily = download(syms, period="5d", interval="1d")
    intra = download(syms, period="1d", interval="5m")
    for sym, iid in idmap.items():
        if sym not in daily or iid not in doc["s"]:
            continue
        pts = decode(doc["s"][iid])
        recent = [(ix.date(), float(c)) for ix, c in daily[sym]["Close"].items()]
        merged = {d: v for d, v in pts}
        merged.update({d: v for d, v in recent})
        pts = sorted(merged.items())
        stamp = None
        if sym in intra:
            last_ix = intra[sym].index[-1]
            try:
                stamp = last_ix.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                stamp = None
            lastp = float(intra[sym]["Close"].iloc[-1])
            if pts and last_ix.date() == pts[-1][0]:
                pts[-1] = (pts[-1][0], lastp)
        doc["s"][iid] = encode(pts)
        q = quote_from(pts, stamp); q["sym"] = sym
        doc["q"][iid] = q
    doc["mode"] = "quotes"
    save(doc)


if __name__ == "__main__":
    (full if (sys.argv[1:] or ["quotes"])[0] == "full" else quotes)()
