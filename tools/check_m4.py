#!/usr/bin/env python3
"""Grade the M4 tool.  Usage: check_m4.py PROJECT_DIR [--seeds N N N]

PROJECT_DIR contains organize.py, tests/ and AGENTS.md.  organize.py is run on
fresh messy folders (new random seeds unless --seeds is given) without any
human input:
  python3 organize.py FOLDER            -> dry run: must print a plan and change NOTHING
  python3 organize.py FOLDER --apply    -> renames; must write FOLDER/moves.csv (old,new)
and check_mission.py m1 must pass afterwards.  Exit code 0 = pass, 1 = fail.
"""
import argparse
import csv
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_messy_folder as gen  # noqa: E402


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120, **kw)


def check_seed(project, seed, work):
    box = work / f"box_{seed}"
    folder = box / "m1"
    gen.write("m1", seed, folder)
    # The seed file is hidden from the tool (a tool must not regenerate the answers); restored before grading.
    hold = work / f"hold_{seed}"
    hold.mkdir()
    shutil.move(str(folder / ".mission.json"), str(hold / ".mission.json"))
    before = snapshot(folder)
    problems = []
    try:
        dry = run([sys.executable, str(project / "organize.py"), str(folder)])
    except subprocess.TimeoutExpired:
        return ["dry run timed out (does it wait for input?) / ドライランがタイムアウト"]
    if dry.returncode != 0:
        problems.append(f"dry run exited {dry.returncode}: {dry.stderr.strip()[-200:]}")
    if snapshot(folder) != before:
        problems.append("dry run changed the folder (must change nothing) / ドライランでフォルダが変更された")
        return problems
    if "->" not in dry.stdout and "→" not in dry.stdout:
        problems.append("dry run printed no 'old -> new' plan / 計画が表示されない")
    try:
        app = run([sys.executable, str(project / "organize.py"), str(folder), "--apply"])
    except subprocess.TimeoutExpired:
        return problems + ["--apply timed out / --apply がタイムアウト"]
    if app.returncode != 0:
        problems.append(f"--apply exited {app.returncode}: {app.stderr.strip()[-200:]}")
    if sorted(p.name for p in box.iterdir()) != ["m1"]:
        problems.append("the tool created files outside FOLDER / FOLDER の外にファイルを作った")
    shutil.move(str(hold / ".mission.json"), str(folder / ".mission.json"))
    moves = folder / "moves.csv"
    if not moves.is_file():
        problems.append("moves.csv missing after --apply / moves.csv がない")
    else:
        with moves.open(newline="", encoding="utf-8") as f:
            if csv.DictReader(f).fieldnames != ["old", "new"]:
                problems.append("moves.csv header must be old,new")
    chk = run([sys.executable, str(HERE / "check_mission.py"), "m1", str(folder)])
    if chk.returncode != 0:
        problems.append("check_mission m1 failed:\n" + "\n".join("      " + l for l in chk.stdout.splitlines()[:8]))
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("project")
    ap.add_argument("--seeds", nargs="+", type=int)
    ap.add_argument("--no-pytest", action="store_true")
    a = ap.parse_args()
    project = Path(a.project).expanduser().resolve()
    seeds = a.seeds or random.sample(range(1000, 10000), 3)
    results = []
    if not (project / "organize.py").is_file():
        print("FAIL  organize.py not found / organize.py がありません")
        return 1
    agents = project / "AGENTS.md"
    text = agents.read_text(encoding="utf-8", errors="replace").lower() if agents.is_file() else ""
    ok = "delete" in text and "_run" in text and "dry" in text
    results.append(("AGENTS.md (naming rule, never delete, dry run default)", ok,
                    "OK" if ok else "missing, or lacks the naming rule / 'delete' / 'dry run'"))
    with tempfile.TemporaryDirectory() as tmp:
        for s in seeds:
            probs = check_seed(project, s, Path(tmp))
            results.append((f"fresh seed {s}", not probs, "OK" if not probs else "\n    ".join(probs)))
    if not a.no_pytest:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=project,
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300)
        tail = (r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]
        results.append(("your pytest", r.returncode == 0, tail))
    print("[M4]")
    for label, good, detail in results:
        print(f"  {'PASS' if good else 'FAIL'}  {label}: {detail}")
    passed = all(g for _, g, _ in results)
    print("RESULT / 結果:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
