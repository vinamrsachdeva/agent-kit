#!/usr/bin/env python3
"""Read boot.dev course content from its public API, and replicate lessons locally.

  bootdev.py course  <course-slug|url>                  chapters, numbered
  bootdev.py chapter <course-slug|url> <chapter-n|slug> lessons: n, type, title, uuid, url
  bootdev.py lesson  <lesson-uuid|url>                  readme + type data (choice answer key last)
  bootdev.py fetch   <lesson-uuid|url> [dir] [--force]  write a local replica of a code lesson
                                                        (dir defaults to bootdev/<course>/<chapter>/<lesson>)
  bootdev.py check   <dir>                              run a replica: PASS / FAIL

Public endpoints only, so no login and no progress: the user's progress lives on boot.dev.
Stdlib only.
"""

import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.boot.dev/v1/static"
SITE = "https://www.boot.dev"
META = ".bootdev-lesson.json"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

# How `check` runs a replica, per language. {main} / {test} are file names.
RUN = {
    "js": ["node", "{main}"],
    "py": [sys.executable, "{main}"],
    "ts": ["npx", "--yes", "tsx", "{main}"],
    "go": ["go", "run", "."],
}
# Each language's commands run in order; the first failure fails the check.
TSC = ["npx", "--yes", "-p", "typescript", "tsc", "--noEmit", "--strict", "--skipLibCheck",
       "--target", "es2022", "--module", "esnext", "--moduleResolution", "bundler", "{ts}"]
TEST = {
    "js": [["node", "{test}"]],
    "py": [[sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "{test}"]],
    "ts": [TSC, ["npx", "--yes", "tsx", "{test}"]],  # tsc catches type-level tests; tsx strips types
    "go": [["go", "test", "./..."]],
}


def get(path):
    # boot.dev's CDN rejects urllib's default User-Agent.
    req = urllib.request.Request(f"{API}/{path}", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"GET {API}/{path}: HTTP {e.code}")


def course(ref):
    m = UUID.search(ref)
    if m:
        return get(f"courses/{m.group()}")
    slug = ref.rstrip("/").split("/")[-1]
    return get(f"courses/{get(f'courses/slug/{slug}')['course']['uuid']}")


def chapter(c, ref):
    chs = c["chapters"]
    if ref.isdigit() and 1 <= int(ref) <= len(chs):
        return int(ref), chs[int(ref) - 1]
    for i, ch in enumerate(chs, 1):
        if ref.lower() in (ch["slug"].lower(), ch["title"].lower()):
            return i, ch
    sys.exit(f"no chapter {ref!r}; run `course` to list them")


def lesson(ref):
    m = UUID.search(ref)
    if not m:
        sys.exit("pass a lesson uuid or a boot.dev/lessons/<uuid> url")
    return get(f"lessons/{m.group()}")["lesson"]


def data(l):
    """The lesson's type-specific payload: (key, dict)."""
    for k, v in l.items():
        if k.startswith("lessonData") and v:
            return k, v
    return None, {}


def cmd_course(a):
    c = course(a.course)
    print(f"{c['title']}  ({c['slug']}, {c['numLessons']} lessons)")
    for i, ch in enumerate(c["chapters"], 1):
        print(f"{i:>3}. {ch['title']}  [{ch['slug']}]  {len(ch['lessons'])} lessons")


def cmd_chapter(a):
    c = course(a.course)
    n, ch = chapter(c, a.chapter)
    print(f"Ch {n}: {ch['title']}  ({c['title']})")
    for i, l in enumerate(ch["lessons"], 1):
        t = l["type"].removeprefix("type_")
        print(f"{i:>3}. {t:<15} {l['title']:<40} {l['uuid']}  {SITE}/lessons/{l['uuid']}")


def cmd_lesson(a):
    l = lesson(a.lesson)
    key, d = data(l)
    print(f"# Ch {l.get('chapterNumber')} L{l.get('lessonNumber')}: {l['title']}")
    print(f"type: {l['type']}   course: {l['courseTitle']}   url: {SITE}/lessons/{l['uuid']}\n")
    print(d.get("readme", "").strip(), "\n")
    skip = ("readme", "questions", "starterFiles", "containsCompleteDir", "solutionFiles")
    rest = {k: v for k, v in d.items() if k not in skip and v not in (None, "")}
    if "starterFiles" in d:
        print("## Starter files")
        for f in d["starterFiles"]:
            flags = ",".join(x for x, on in (("hidden", f["isHidden"]), ("readonly", f["isReadonly"])) if on)
            print(f"--- {f['name']}{f' ({flags})' if flags else ''}")
            print(f["content"])
    if "codeExpectedOutput" in rest:
        print("## Expected output\n" + rest.pop("codeExpectedOutput"))
    if rest:
        print("## Data\n" + json.dumps(rest, indent=1))
    if d.get("questions"):
        print("## Questions")
        for i, q in enumerate(d["questions"], 1):
            print(f"{i}. {q['question']}")
            for o in q["answers"]:
                print(f"   - {o}")
        print("\n## Answer key (grading only; keep it out of chat)")
        for i, q in enumerate(d["questions"], 1):
            print(f"{i}. {q['answer']}")


def cmd_fetch(a):
    l = lesson(a.lesson)
    key, d = data(l)
    if "starterFiles" not in d:
        sys.exit(f"{l['type']} has no code to replicate; run `lesson` and see LESSON-TYPES.md")
    out = Path(a.dir or f"bootdev/{l['courseSlug']}/{l['chapterSlug']}/{l['slug']}")
    out.mkdir(parents=True, exist_ok=True)
    lang = d["progLang"]
    for f in d["starterFiles"]:
        p = out / f["name"]
        if p.exists() and not a.force:
            print(f"keep  {p}  (exists; --force overwrites)")
            continue
        body = f["content"]
        if lang == "js" and f["name"] == "unit_test.js":
            # Locally, run the submit cases too: that's what boot.dev's Submit runs.
            body = body.replace("let withSubmit = false", "let withSubmit = true")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
        print(f"wrote {p}")
    if lang == "js" and not (out / "package.json").exists():
        (out / "package.json").write_text('{ "type": "module" }\n')
    (out / "README.md").write_text(d["readme"])
    if "codeExpectedOutput" in d:
        (out / "expected_output.txt").write_text(d["codeExpectedOutput"])
    editable = [f["name"] for f in d["starterFiles"] if not f["isReadonly"]]
    tests = [f["name"] for f in d["starterFiles"] if re.search(r"_test\.\w+$", f["name"])]
    meta = {"uuid": l["uuid"], "title": l["title"], "type": l["type"], "lang": lang,
            "edit": editable, "main": (editable or [d["starterFiles"][0]["name"]])[0],
            "test": tests[0] if tests else None}
    (out / META).write_text(json.dumps(meta, indent=1))
    print(f"\nedit: {', '.join(editable)}\ncheck: {sys.argv[0]} check {out}")


def run(argv, cwd):
    if not shutil.which(argv[0]):
        sys.exit(f"`{argv[0]}` is not installed; complete this lesson on boot.dev instead")
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def norm(s):
    return [line.rstrip() for line in s.rstrip().splitlines()]


def cmd_check(a):
    out = Path(a.dir)
    m = json.loads((out / META).read_text())
    lang = m["lang"]
    if m["type"] == "type_code":
        if lang not in RUN:
            sys.exit(f"no runner for {lang}; compare by hand with expected_output.txt")
        code, so, se = run([x.format(main=m["main"]) for x in RUN[lang]], out)
        print(so, end="")
        if se:
            print(se, end="", file=sys.stderr)
        want = (out / "expected_output.txt").read_text()
        if norm(so) == norm(want):
            print("\nPASS")
            return
        print("\nFAIL: output differs from expected_output.txt")
        print("\n".join(difflib.unified_diff(norm(want), norm(so), "expected", "got", lineterm="")))
        sys.exit(1)
    if lang not in TEST or not m["test"]:
        sys.exit(f"no test runner for {lang}; complete this lesson on boot.dev instead")
    ts = [f.name for f in out.glob("*.ts")]
    for argv in TEST[lang]:
        argv = [a for x in argv for a in (ts if x == "{ts}" else [x.format(test=m["test"])])]
        code, so, se = run(argv, out)
        print(so, end="")
        if se:
            print(se, end="", file=sys.stderr)
        if code != 0 or "✘ Fail" in so:
            print("\nFAIL")
            sys.exit(1)
    print("\nPASS")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("course"); s.add_argument("course"); s.set_defaults(f=cmd_course)
    s = sub.add_parser("chapter"); s.add_argument("course"); s.add_argument("chapter"); s.set_defaults(f=cmd_chapter)
    s = sub.add_parser("lesson"); s.add_argument("lesson"); s.set_defaults(f=cmd_lesson)
    s = sub.add_parser("fetch"); s.add_argument("lesson"); s.add_argument("dir", nargs="?")
    s.add_argument("--force", action="store_true"); s.set_defaults(f=cmd_fetch)
    s = sub.add_parser("check"); s.add_argument("dir"); s.set_defaults(f=cmd_check)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
