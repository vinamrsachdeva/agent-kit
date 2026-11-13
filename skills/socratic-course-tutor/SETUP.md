# Setting up a site

Setup builds a site's **adapter**: how to read its courses, and how each of its lesson
types ends locally the way it ends on the site. It runs once per site, so later
sessions skip it. Courses on most sites share their shapes; when a course has its own
(a Coursera course with custom autograders), setup also runs once for that course.

Write the adapter to `sites/<site>/` in this skill's folder (`<site>` is the bare
domain, e.g. `boot.dev`). When that folder is read-only, such as a plugin cache, use
`~/.local/share/socratic-course-tutor/sites/<site>/`.

## Steps

1. **Content access.** Try these in order, and stop at the first that returns a
   lesson's content as data:
   1. a JSON API: open a lesson page in the browser and watch its network requests,
      look for JSON embedded in the HTML (`__NEXT_DATA__`, `__NUXT_DATA__`,
      `window.__INITIAL_STATE__`), or grep the site's JS bundles for API paths.
      Embedded JSON often holds only part of the data; follow it to the endpoint that
      holds the rest;
   2. an open-source client or CLI for the site (search GitHub), which names its
      endpoints;
   3. the page HTML, fetched directly;
   4. the user's logged-in browser, reading pages as text.

   Use public endpoints, or the browser session the user is already logged in to.
   Leave stored tokens and credential files on disk unread; when content needs a
   login the browser lacks, ask the user to log in there.

   Done when you can list the course's units, list a unit's lessons with each
   lesson's type, and print one lesson's full content.

2. **Lesson types.** Walk the whole course outline and collect every distinct lesson
   type. Open one lesson of each type and record:
   - its content fields, and where the lesson's text lives;
   - what the learner submits, and how the site grades it: output match, visible or
     hidden tests, cases that run only on submit, an AI grader, peer review;
   - whether answer keys or solutions are reachable, in the data or at their own
     endpoint;
   - how the site runs code, when it does: its runner or worker script decides module
     mode, console formatting, and which cases run on Submit;
   - which kind in SKILL.md's "Ending a lesson" it maps to.

   Done when every type in the course outline has a record. Then open one lesson from
   one or two other courses on the site: when their shapes match, the adapter's scope
   is the site; when they differ, it is per course.

3. **Write the adapter.**
   - `ADAPTER.md`, from the template below.
   - `site.py` (stdlib Python, executable), when content is reachable without a
     browser, with these subcommands:

         outline <course>          the course's units, numbered
         unit    <course> <unit>   the unit's lessons: number, type, title, id, url
         lesson  <id|url>          the lesson's text and exercise data; answer key and
                                   test code last, labelled
         fetch   <id|url> [dir]    the replica of a code lesson; dir defaults to
                                   <course>/<unit>/<lesson> under the current directory

     `<course>` takes a slug or URL; `<unit>` a number, slug, or title. `fetch` writes the starter files verbatim, `expected_output.txt` for an `output`
     lesson, and `.lesson.json` (contract below). It makes only the edits that make
     local grading match the site's, such as switching on submit-only test cases,
     plus what the language needs to run (a `package.json` with `"type": "module"`
     for ES-module JS). When the site wraps the user's code (its own console
     formatting, a harness), write that wrapper too and make it `main`; `edit` still
     names the user's files. When the site grades with its own test harness, put a
     runner for it in the adapter's folder, have `fetch` copy it in, and point `test`
     at it; it reports in `replica.py`'s form (below). Download site code only from
     the site's own origin: `check` runs it unsandboxed. Every error from an unexpected response names "When a site
     changes" in SKILL.md.
   - For a browser-only site, `ADAPTER.md` lists the pages and steps instead.

4. **Verify.** Done when, on the target course:
   - `outline`, `unit`, and `lesson` succeed, and `lesson` has printed one lesson of
     every type;
   - for every code type that runs outside the site (a DOM or the site's own
     environment makes a type `site-only`), `fetch` then `scripts/replica.py check <dir>` prints FAIL on
     the untouched starter files, and PASS on a scratch copy solved with the site's
     solution when it is public, or with yours. Keep the solution out of chat, and
     delete the copy.

5. **Tell the user** which types end locally, which end only on the site, and any gap
   between the local pass and the site's.

## Per course

When an adapter's scope is per course, or a course has a type its adapter lacks, run
steps 2 to 4 for that course only. Put what is specific to it in
`sites/<site>/courses/<course>.md`, and add new types to `ADAPTER.md`.

## `.lesson.json`

`scripts/replica.py check` reads it:

    {
      "site": "boot.dev",
      "id": "<lesson id>",
      "title": "...",
      "type": "<the site's type name>",
      "mode": "output | tests",
      "lang": "js | py | ts | go",
      "edit": ["files the user edits"],
      "main": "file run in output mode: the user's file, or the site's wrapper",
      "test": "test file run in tests mode (null for go)"
    }

`check` passes in `output` mode when stdout matches `expected_output.txt`, and in
`tests` mode when every test command exits 0 and prints no `✘ Fail`. A language
outside `replica.py`'s runners gets a runner added there; a site's own harness stays
in the adapter.

## ADAPTER.md template

    # <site>

    Scope: site | per course (why)
    Content: <API base, or browser only>; auth: none | the user's logged-in browser
    Progress: <readable or not, and how>
    Commands: `sites/<site>/site.py` (subcommands per SETUP.md), or the browser steps

    | Site type | Kind | On the site | Local replica | Local pass |
    | --- | --- | --- | --- | --- |

    ## Gotchas

    <what no response confesses: required headers, submit-only cases, flags fetch flips>
