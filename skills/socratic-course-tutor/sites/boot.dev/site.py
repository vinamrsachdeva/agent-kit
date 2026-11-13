#!/usr/bin/env python3
"""Boot.dev site adapter: read course content from its public API, replicate code lessons.

  site.py outline <course-slug|url>                  chapters, numbered
  site.py unit    <course-slug|url> <chapter-n|slug> lessons: n, type, title, uuid, url
  site.py lesson  <lesson-uuid|url>                  readme + type data (choice answer key last)
  site.py fetch   <lesson-uuid|url> [dir] [--force]  write a local replica of a code lesson
                                                     (dir defaults to bootdev/<course>/<chapter>/<lesson>)

Grade a replica with the skill's scripts/replica.py check <dir>.

Public endpoints only, so no login and no progress: the user's progress lives on boot.dev.
Stdlib only.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.boot.dev/v1/static"
SITE = "https://www.boot.dev"
META = ".lesson.json"  # contract: SETUP.md
DRIFT = "Boot.dev's API may have changed: see 'When a site changes' in SKILL.md"
# Every type ADAPTER.md covers; a type outside this set is drift.
KNOWN = {"type_code", "type_code_tests", "type_choice", "type_interview_chat", "type_text_input",
         "type_cli", "type_shell", "type_github_checks"}
# JS output lessons: the site runs main.js as an ES module in www.boot.dev/js_worker.js, whose
# console.log formats values with its own prepareToPrint, not Node's util.inspect (Node wraps long
# arrays and cuts deep objects; the site prints them on one line, in full). fetch writes this runner
# as `main`, so prints match the site's. If the site's formatting changes, update it from that worker.
JS_RUNNER = "_site_run.js"
JS_RUNNER_SRC = r"""// Written by sites/boot.dev/site.py fetch: runs main.js the way www.boot.dev/js_worker.js does.
function prepareToPrint(obj, addQuotes = false, seen = new Set()) {
  if (obj === undefined) return "undefined";
  if (obj === null) return "null";
  if (typeof obj === "function") return obj.toString();
  if (seen.has(obj)) return "[Circular]";
  if (typeof obj === "object" && obj !== null) seen.add(obj);
  if (Array.isArray(obj)) return `[ ${obj.map((el) => prepareToPrint(el, true, seen)).join(", ")} ]`;
  if (typeof obj === "string") return addQuotes ? `'${obj}'` : obj;
  if (obj instanceof Set)
    return `Set(${obj.size}) { ${[...obj].map((el) => prepareToPrint(el, true, seen)).join(", ")} }`;
  if (obj instanceof Map)
    return `Map(${obj.size}) { ${[...obj].map(([k, v]) => `${k} => ${prepareToPrint(v, true, seen)}`).join(", ")} }`;
  if (typeof obj === "object")
    return `{ ${Object.entries(obj).map(([k, v]) => `${k}: ${prepareToPrint(v, true, seen)}`).join(", ")} }`;
  return obj.toString ? obj.toString() : String(obj);
}
const write = (s) => process.stdout.write(s + "\n");
console.log = (...xs) => write(xs.map((x) => prepareToPrint(x)).join(" "));
await import("./%s");
"""
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def get(path):
    # boot.dev's CDN rejects urllib's default User-Agent.
    req = urllib.request.Request(f"{API}/{path}", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        hint = "check the slug or uuid; if it is right, " if e.code == 404 else ""
        sys.exit(f"GET {API}/{path}: HTTP {e.code}. {hint}{DRIFT}")
    except json.JSONDecodeError:
        sys.exit(f"GET {API}/{path}: not JSON. {DRIFT}")


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
    sys.exit(f"no chapter {ref!r}; run `outline` to list them")


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
    if l["type"] not in KNOWN:
        print(f"NEW LESSON TYPE {l['type']}: add it to ADAPTER.md and KNOWN", file=sys.stderr)
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
        sys.exit(f"{l['type']} has no code to replicate; run `lesson` and see ADAPTER.md")
    out = Path(a.dir or f"{l['courseSlug']}/{l['chapterSlug']}/{l['slug']}")
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
    if "codeExpectedOutput" in d:
        (out / "expected_output.txt").write_text(d["codeExpectedOutput"])
    editable = [f["name"] for f in d["starterFiles"] if not f["isReadonly"]]
    main = (editable or [d["starterFiles"][0]["name"]])[0]
    if lang == "js" and l["type"] == "type_code":
        (out / JS_RUNNER).write_text(JS_RUNNER_SRC % main)
        main = JS_RUNNER
    tests = [f["name"] for f in d["starterFiles"] if re.search(r"_test\.\w+$", f["name"])]
    meta = {"site": "boot.dev", "id": l["uuid"], "title": l["title"], "type": l["type"],
            "mode": "output" if l["type"] == "type_code" else "tests", "lang": lang,
            "edit": editable, "main": main,
            "test": tests[0] if tests else None}
    (out / META).write_text(json.dumps(meta, indent=1))
    replica = Path(__file__).resolve().parents[2] / "scripts" / "replica.py"
    print(f"\nedit: {', '.join(editable)}\ncheck: {replica} check {out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("outline"); s.add_argument("course"); s.set_defaults(f=cmd_course)
    s = sub.add_parser("unit"); s.add_argument("course"); s.add_argument("chapter"); s.set_defaults(f=cmd_chapter)
    s = sub.add_parser("lesson"); s.add_argument("lesson"); s.set_defaults(f=cmd_lesson)
    s = sub.add_parser("fetch"); s.add_argument("lesson"); s.add_argument("dir", nargs="?")
    s.add_argument("--force", action="store_true"); s.set_defaults(f=cmd_fetch)
    a = p.parse_args()
    try:
        a.f(a)
    except (KeyError, TypeError, IndexError) as e:
        sys.exit(f"unexpected response shape ({e!r}). {DRIFT}")


if __name__ == "__main__":
    main()
