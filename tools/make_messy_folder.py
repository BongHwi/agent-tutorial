#!/usr/bin/env python3
"""Generate a deterministic messy lab folder for the AI-agent tutorial missions.

Usage: make_messy_folder.py --mission {m1,m2} --seed N --out DIR

The folder content depends only on (mission, seed). No answer key is written;
check_mission.py recomputes the expectations by calling build() again.
"""
import argparse
import json
import random
import struct
import sys
import zlib
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

VERSION = 1
KIND_EXT = {"data": "csv", "scope": "txt", "plot": "png", "note": "md"}
KIND_SUBDIR = {"data": "raw", "scope": "raw", "plot": "plots", "note": "notes"}
START = date(2026, 10, 1)
N_DAYS = 61  # Oct 1 .. Nov 30
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
N_M1_CLASSIFIED = 57
N_M1_UNSORTED = 3
N_M1_DATELESS = 5
N_M2_BASE = 55
N_M2_DUPES = 3
N_M2_COLLISIONS = 2


@dataclass
class Entry:
    orig: str          # relative path of the generated file
    data: bytes
    target: str        # m1: exact expected relative path; m2: expected directory ("a/b/")
    group: int = -1    # m2: exact-duplicate group id, -1 if none


def canonical(kind, run, d, v):
    return f"{kind}_run{run:03d}_{d:%Y%m%d}_v{v}.{KIND_EXT[kind]}"


def png_bytes(rng):
    w = h = 4
    raw = b"".join(b"\x00" + bytes(rng.randrange(256) for _ in range(w * 3)) for _ in range(h))

    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def content(rng, kind, run, d, dateline=False):
    if kind == "plot":
        return png_bytes(rng)
    head = f"# date: {d:%Y-%m-%d}\n" if dateline else ""
    if kind == "data":
        rows = "".join(f"{rng.randint(0, 99999)},{rng.randint(0, 4095)}\n" for _ in range(8))
        return (head + "time_ns,adc\n" + rows).encode()
    if kind == "scope":
        rows = "".join(f"ch{c} {rng.uniform(-1, 1):.4f} V\n" for c in range(1, 5))
        return (head + f"scope trace, run {run}\n" + rows).encode()
    body = f"- threshold {rng.randint(10, 90)} mV\n- temperature {rng.uniform(15, 25):.1f} C\n"
    return (head + f"# Run notes (run {run})\n" + body).encode()


def _specs(rng, n):
    seen, out = set(), []
    while len(out) < n:
        key = (rng.choice(list(KIND_EXT)), rng.randint(1, 150),
               START + timedelta(days=rng.randrange(N_DAYS)), rng.randint(1, 3))
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _date_str(rng, d):
    fmts = [
        lambda: f"{d:%Y%m%d}",
        lambda: f"{d:%Y-%m-%d}",
        lambda: f"{d.day:02d}{MONTHS[d.month - 1]}{d.year}",
        lambda: f"{d:%m_%d_%Y}",
    ]
    # MM_DD_YYYY is only unambiguous when the day cannot be a month.
    i = rng.randrange(4 if d.day > 12 else 3)
    return fmts[i]()


def messy_name(rng, kind, run, d, v, with_date=True):
    run_s = rng.choice([f"Run{run}", f"run_{run:03d}", f"R{run}", f"run-{run}"])
    parts = [run_s, f"v{v}"]
    if with_date:
        parts.append(_date_str(rng, d))
    if rng.random() < 0.3:
        parts.append(rng.choice(["scan", "detector", "tdc", "beam", "sample"]))
    if rng.random() < 0.4:
        parts.append(rng.choice(["final", "new", "copy", "FINAL"]))
    rng.shuffle(parts)
    stem = rng.choice([" ", "_", "-"]).join(parts)
    stem = rng.choice([lambda s: s, str.lower, str.upper])(stem)
    if rng.random() < 0.12:
        stem += " (2)"
    ext = KIND_EXT[kind]
    return f"{stem}.{ext.upper() if rng.random() < 0.3 else ext}"


def _build_m1(rng):
    specs = _specs(rng, N_M1_CLASSIFIED)
    dateless = set(rng.sample([i for i, s in enumerate(specs) if s[0] != "plot"], N_M1_DATELESS))
    entries, used = [], set()
    for i, (kind, run, d, v) in enumerate(specs):
        while True:
            name = messy_name(rng, kind, run, d, v, with_date=i not in dateless)
            if name.lower() not in used:
                used.add(name.lower())
                break
        entries.append(Entry(name, content(rng, kind, run, d, dateline=i in dateless),
                             canonical(kind, run, d, v)))
    unsorted = [
        (f"IMG_{rng.randint(1, 9999):04d}.png", png_bytes(rng)),
        ("Untitled document.md", f"TODO: ask later ({rng.randint(1, 10**6)})\n".encode()),
        ("scratch.txt", f"{rng.randint(1, 10**6)} {rng.randint(1, 10**6)}\n".encode()),
    ]
    for name, data in unsorted:
        entries.append(Entry(name, data, "_unsorted/" + name))
    rng.shuffle(entries)
    return entries


def _build_m2(rng):
    specs = _specs(rng, N_M2_BASE)
    seen = set(specs)
    entries = []
    for kind, run, d, v in specs:
        sub = KIND_SUBDIR[kind]
        entries.append(Entry(canonical(kind, run, d, v), content(rng, kind, run, d),
                             f"{d:%Y%m%d}/run{run:03d}/{sub}/"))
    order = list(range(N_M2_BASE))
    rng.shuffle(order)
    dup_src, col_src = order[:N_M2_DUPES], order[N_M2_DUPES:N_M2_DUPES + N_M2_COLLISIONS]
    for g, i in enumerate(dup_src):
        kind, run, d, v = specs[i]
        nv = next(x for x in (1, 2, 3) if (kind, run, d, x) not in seen)
        seen.add((kind, run, d, nv))
        entries[i].group = g
        entries.append(Entry(canonical(kind, run, d, nv), entries[i].data, entries[i].target, g))
    for i in col_src:
        kind, run, d, v = specs[i]
        entries.append(Entry("laptop_copy/" + canonical(kind, run, d, v),
                             content(rng, kind, run, d), entries[i].target))
    rng.shuffle(entries)
    return entries


def build(mission, seed):
    rng = random.Random(f"{mission}:{seed}:{VERSION}")
    entries = _build_m1(rng) if mission == "m1" else _build_m2(rng)
    assert len({e.data for e in entries}) == len(entries) - (N_M2_DUPES if mission == "m2" else 0)
    return entries


def write(mission, seed, out):
    out = Path(out).expanduser()
    if out.exists() and any(out.iterdir()):
        sys.exit(f"error: {out} is not empty / フォルダが空ではありません")
    out.mkdir(parents=True, exist_ok=True)
    entries = build(mission, seed)
    for e in entries:
        p = out / e.orig
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(e.data)
    (out / ".mission.json").write_text(
        json.dumps({"mission": mission, "seed": seed, "version": VERSION}) + "\n")
    return len(entries)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mission", required=True, choices=["m1", "m2"])
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    n = write(a.mission, a.seed, a.out)
    print(f"{a.mission} seed={a.seed}: {n} files -> {a.out}")


if __name__ == "__main__":
    main()
