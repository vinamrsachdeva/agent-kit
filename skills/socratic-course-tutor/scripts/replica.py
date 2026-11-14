#!/usr/bin/env python3
"""Run a local replica of a code exercise and grade it: PASS / FAIL.

  replica.py check <dir>

<dir> holds the exercise's starter files plus `.lesson.json`, written by a site
adapter's `fetch` (see SETUP.md for the contract). Two modes:

  output  run `main`; stdout must match expected_output.txt (trailing whitespace ignored)
  tests   run the language's test commands in order; each must exit 0 and print no "✘ Fail"

Stdlib only.
"""

import argparse
import difflib
import json
import shutil
import subprocess
import sys
from pathlib import Path

META = ".lesson.json"

# How `output` mode runs `main`, per language.
RUN = {
    "js": ["node", "{main}"],
    "py": [sys.executable, "{main}"],
    "ts": ["npx", "--yes", "tsx", "{main}"],
    "go": ["go", "run", "."],
}
# `tests` mode: each language's commands run in order; the first failure fails the check.
TSC = ["npx", "--yes", "-p", "typescript", "tsc", "--noEmit", "--strict", "--skipLibCheck",
       "--target", "es2022", "--module", "esnext", "--moduleResolution", "bundler", "{ts}"]
TEST = {
    "js": [["node", "{test}"]],
    "py": [[sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "{test}"]],
    "ts": [TSC, ["npx", "--yes", "tsx", "{test}"]],  # tsc catches type-level tests; tsx strips types
    "go": [["go", "test", "./..."]],
}


def run(argv, cwd):
    if not shutil.which(argv[0]):
        sys.exit(f"`{argv[0]}` is not installed; install it, or complete this lesson on the site")
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    print(p.stdout, end="")
    if p.stderr:
        print(p.stderr, end="", file=sys.stderr)
    return p.returncode, p.stdout


def norm(s):
    return [line.rstrip() for line in s.rstrip().splitlines()]


def check(out):
    m = json.loads((out / META).read_text())
    lang, mode = m["lang"], m["mode"]
    if mode == "output":
        if lang not in RUN:
            sys.exit(f"no runner for {lang}; add it to RUN in this script (SETUP.md), or compare by hand with expected_output.txt")
        _, so = run([x.format(main=m["main"]) for x in RUN[lang]], out)
        want = (out / "expected_output.txt").read_text()
        if norm(so) == norm(want):
            print("\nPASS")
            return
        print("\nFAIL: output differs from expected_output.txt")
        print("\n".join(difflib.unified_diff(norm(want), norm(so), "expected", "got", lineterm="")))
        sys.exit(1)
    if mode != "tests" or lang not in TEST or (not m.get("test") and lang != "go"):  # go test finds its own
        sys.exit(f"no test runner for mode={mode} lang={lang}; add it to TEST in this script (SETUP.md), or complete this lesson on the site")
    ts = [f.name for f in out.glob("*.ts")]
    for argv in TEST[lang]:
        argv = [a for x in argv for a in (ts if x == "{ts}" else [x.format(test=m["test"])])]
        code, so = run(argv, out)
        if code != 0 or "✘ Fail" in so:
            print("\nFAIL")
            sys.exit(1)
    print("\nPASS")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("check")
    s.add_argument("dir")
    a = p.parse_args()
    check(Path(a.dir))


if __name__ == "__main__":
    main()
