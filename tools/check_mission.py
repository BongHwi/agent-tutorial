#!/usr/bin/env python3
"""Check a finished mission folder.  Usage: check_mission.py {m1,m2} DIR

Exit code 0 = pass, 1 = fail.  Expectations are recomputed from DIR/.mission.json.
"""
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_messy_folder as gen  # noqa: E402

THRESHOLD = 0.95
IGNORED_TOP = {".mission.json", "moves.csv", "undo.py"}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def scan(root):
    files = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if not p.is_file() or ".git" in rel.parts or p.name == ".DS_Store":
            continue
        if p.name == ".mission.json" or (len(rel.parts) == 1 and rel.name in IGNORED_TOP):
            continue
        files[rel.as_posix()] = sha(p)
    return files


def score(mission, expected, actual):
    """Return (n_correct, hints). expected: list of Entry; actual: {path: hash}."""
    by_hash = defaultdict(list)
    for path, h in actual.items():
        by_hash[h].append(path)
    exp_by_hash = defaultdict(list)
    for e in expected:
        exp_by_hash[hashlib.sha256(e.data).hexdigest()].append(e)
    correct, hints = 0, []
    for h, entries in exp_by_hash.items():
        paths = by_hash.get(h, [])
        if mission == "m1":
            e = entries[0]
            if paths == [e.target]:
                correct += 1
            else:
                hints.append(f"{e.orig}: {paths[0] if paths else '(missing)'} -> expected {e.target}")
        else:
            in_dir = [p for p in paths if str(PurePosixPath(p).parent) + "/" == entries[0].target]
            if len(entries) == 1:
                ok = paths == in_dir and len(paths) == 1
                msg = f"{entries[0].orig}: {paths[0] if paths else '(missing)'} -> expected in {entries[0].target}"
            else:  # exact duplicates: one kept in the tree, the rest under _duplicates/
                rest = [p for p in paths if p not in in_dir]
                ok = len(in_dir) == 1 and len(rest) == len(entries) - 1 and all(
                    p.startswith("_duplicates/") for p in rest)
                msg = f"duplicates {[e.orig for e in entries]}: one in {entries[0].target}, rest in _duplicates/"
            if ok:
                correct += len(entries)
            else:
                hints.append(msg)
    return correct, hints


def check_moves(root, expected, actual):
    """m2 extras. Returns list of (label, ok, detail)."""
    out = []
    moves = root / "moves.csv"
    rows_ok = False
    detail = "missing / なし"
    if moves.is_file():
        try:
            with moves.open(newline="", encoding="utf-8-sig") as f:
                rd = csv.DictReader(f)
                if rd.fieldnames != ["old", "new"]:
                    detail = f"header must be old,new (got {rd.fieldnames})"
                else:
                    orig = {e.orig for e in expected}
                    rows = list(rd)
                    norm = lambda s: (s or "").removeprefix("./")
                    valid = sum(1 for r in rows if norm(r["old"]) in orig and norm(r["new"]) in actual)
                    rows_ok = valid >= THRESHOLD * len(orig)
                    detail = f"{valid}/{len(orig)} valid rows (old = original relative path, new = current relative path; no absolute paths)"
        except (OSError, UnicodeDecodeError, csv.Error) as exc:
            detail = f"unreadable: {exc}"
    out.append(("moves.csv", rows_ok, detail))
    undo = root / "undo.py"
    ok = False
    detail = "missing / なし"
    if undo.is_file():
        try:
            compile(undo.read_text(encoding="utf-8"), "undo.py", "exec")
            ok, detail = True, "exists, valid Python"
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            detail = f"not valid Python: {exc}"
    out.append(("undo.py", ok, detail))
    return out


def main(argv):
    if len(argv) != 3 or argv[1] not in ("m1", "m2"):
        print("usage: check_mission.py {m1,m2} DIR")
        return 2
    mission, root = argv[1], Path(argv[2]).expanduser()
    meta_path = next((p for p in [root / ".mission.json", *root.rglob(".mission.json")] if p.is_file()), None)
    if meta_path is None:
        print(f"FAIL: {root}/.mission.json not found (did you delete or move the folder? / フォルダを削除・移動していませんか？)")
        return 1
    meta = json.loads(meta_path.read_text())
    if meta.get("mission") != mission or meta.get("version") != gen.VERSION:
        print(f"FAIL: .mission.json is for {meta.get('mission')} v{meta.get('version')}, not {mission} v{gen.VERSION}")
        return 1
    expected = gen.build(mission, meta["seed"])
    actual = scan(root)

    checks = []
    n_exp = len(expected)
    detail = f"{len(actual)}/{n_exp}"
    if len(actual) > n_exp and mission == "m2":
        extra = sorted(p for p in actual if not any(p.endswith(e.orig.split("/")[-1]) for e in expected))
        if extra:
            detail += f" (unexpected files / 予期しないファイル: {', '.join(extra[:5])})"
    elif len(actual) > n_exp:
        known = {e.target.split("/")[-1].lower() for e in expected} | {e.orig.lower() for e in expected}
        extra = sorted(p for p in actual if p.split("/")[-1].lower() not in known)
        if extra:
            detail += f" (unexpected files / 予期しないファイル: {', '.join(extra[:5])})"
    checks.append(("file count / ファイル数", len(actual) == n_exp, detail))
    same = Counter(actual.values()) == Counter(hashlib.sha256(e.data).hexdigest() for e in expected)
    checks.append(("content intact / 内容保持", same,
                   "OK" if same else "a file was lost, modified or added / ファイルの欠落・変更・追加があります"))
    correct, hints = score(mission, expected, actual)
    acc = correct / n_exp
    checks.append(("accuracy / 正確さ", acc >= THRESHOLD,
                   f"{correct}/{n_exp} = {acc:.1%} (required / 基準 {THRESHOLD:.0%})"))
    if mission == "m2":
        checks.extend(check_moves(root, expected, actual))

    print(f"[{mission.upper()}] seed {meta['seed']}")
    for label, ok, detail in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}: {detail}")
    passed = all(ok for _, ok, _ in checks)
    if hints and acc < 1:
        print("  examples of mistakes / 誤りの例:")
        for h in hints[:5]:
            print(f"    - {h}")
    print("RESULT / 結果:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
