# boot.dev

Scope: site. Every course shares one lesson schema.
Content: public API at `https://api.boot.dev/v1/static`; auth: none.
Progress: not readable without the user's token, so the user's word is the record.
Commands: `sites/boot.dev/site.py outline | unit | lesson | fetch`. `lesson` prints every type's readme and data; teach from the readme and set the exercise from the data.

| Site type | Kind | On the site | Local replica | Local pass |
| --- | --- | --- | --- | --- |
| `type_code` | `output` | Submit; stdout must match | `fetch`; the user edits the files under `edit:` | `check` PASS |
| `type_code_tests` | `tests` | Submit; the tests must pass | `fetch` | `check` PASS; it runs the submit cases too, so it is the same bar as Submit |
| `type_choice` | `choice` | Click an answer | `questions` in chat | the answer-key option |
| `type_interview_chat` | `essay` | A chat with Boots until Boot.dev's AI accepts the answer | `studentPrompt` in chat | every point of `acceptanceCriteria`, or of the readme's main claims when it is empty |
| `type_text_input` | `paste` | Paste a command's output | the user runs the readme's command | the output is what that command produces |
| `type_cli` | `paste` | `bootdev run <uuid>` to test, `bootdev run <uuid> -s` to submit, in the user's own project | the user runs each step's `cliCommand.command` plus `; echo "exit: $?"` and pastes the output | it passes every step's tests (`exitCode`, `stdoutContainsAll`, `stdoutContainsNone`), or the user's submit run passes |
| `type_shell` | `paste` | Boot.dev's in-browser terminal | the user runs the commands in their own shell and pastes the last one | it satisfies `shellData.checks` |
| `type_github_checks` | `site-only` | Boot.dev checks the user's GitHub repo | none | Boot.dev only |
| `type_code_sql` | `site-only` | SQL run against the site's database | none: `replica.py` has no SQL runner | Boot.dev only |

## Gotchas

- The CDN returns 403 to urllib's default User-Agent; `site.py` sends `Mozilla/5.0`.
- Submit-only cases. JS/TS: the hidden `unit_test.js` has `let withSubmit = false`, which the site's worker flips on Submit; `fetch` flips it too. Python: `pytest.mark.submit` params, which plain pytest runs. Go: `withSubmit = true` already.
- The site runs JS as ES modules (`www.boot.dev/js_worker.js`); `fetch` writes `package.json` with `"type": "module"`.
- The site's `console.log` is not Node's: it prints long arrays on one line, deep objects in full, a function as its source. For JS output lessons `fetch` writes `_site_run.js`, the worker's formatter, as `main`; the user still edits `main.js`.
- Output lessons grade stdout only, on the site too: a stated constraint ("use an arrow function") is yours to check when you read the user's code.
- TS type-level tests only fail under `tsc`; `replica.py` runs `tsc --strict` before `tsx`.
- Solutions: `lessonData*.solutionFiles` is null; `https://api.boot.dev/v1/lessons/<uuid>/solution` serves them for free lessons (403 for paid). Use it to verify an adapter change; `lesson` leaves it out.
- Only `static/courses/<uuid>` fills `chapters[].lessons`; the slug endpoint and the page's `__NUXT_DATA__` return `lessons: null`.
- The anonymous progress endpoint answers 200 with every lesson incomplete: read it as unknown, not as zero.
- `type_choice` data carries the answer key; `lesson` prints it last, labelled.
