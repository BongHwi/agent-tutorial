#!/usr/bin/env python3
"""Print a short, pasteable environment report.  Exit code 1 if any item FAILs."""
import platform
import re
import subprocess
import sys


def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (r.stdout + r.stderr).strip() if r.returncode == 0 else None


def version_of(text):
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text or "")
    return tuple(int(x or 0) for x in m.groups()) if m else None


def main():
    rows = []
    py = sys.version_info[:3]
    rows.append(("python", "PASS" if py >= (3, 10) else "FAIL", ".".join(map(str, py)),
                 "" if py >= (3, 10) else "Python 3.10+ required / 3.10以上が必要"))

    out = run(["git", "--version"])
    rows.append(("git", "PASS" if out else "FAIL", out or "not found", "" if out else "install git / git をインストール"))

    out = run(["codex", "--version"])
    rows.append(("codex", "PASS" if out else "FAIL", out or "not found", "" if out else "install Codex (see M0) / Codex をインストール (M0参照)"))
    if out:
        login = run(["codex", "login", "status"])
        rows.append(("codex login", "PASS" if login else "FAIL", login or "not logged in?",
                     "" if login else "run `codex login` / `codex login` を実行"))

    out = run(["node", "--version"])
    v = version_of(out)
    if v is None:
        rows.append(("node", "WARN", "not found", "needed in week 2 for DSH (>= 24.9) / 2週目のDSHに必要"))
    elif v < (24, 9):
        rows.append(("node", "WARN", out, "needed >= 24.9 in week 2 for DSH; ignore for now / 2週目のDSHに必要(今は無視可)"))
    else:
        rows.append(("node", "PASS", out, ""))

    print(f"{platform.system()} {platform.machine()}")
    for name, status, value, note in rows:
        print(f"{status:<4} {name:<12} {value}" + (f"  <- {note}" if note else ""))
    return 1 if any(r[1] == "FAIL" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
