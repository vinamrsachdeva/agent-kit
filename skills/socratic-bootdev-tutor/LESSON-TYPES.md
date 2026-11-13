# Ending a lesson, by type

A lesson ends one of two ways; the user picks:

- **On Boot.dev**: the user completes the lesson in their browser on their own, then tells you. Their word is the record; the scripts cannot read progress.
- **Locally**: you replicate the exercise here, and it ends on the local pass condition below. This does not mark the lesson complete on Boot.dev; say so the first time.

`bootdev.py lesson <uuid>` prints every type's readme and data. Teach from the readme; set the exercise from the data.

| Type | On Boot.dev | Local replica | Local pass |
| --- | --- | --- | --- |
| `code` | Submit; stdout must match | `bootdev.py fetch <uuid>`; user edits the files named under `edit:` | `bootdev.py check <dir>` prints PASS (stdout matches `expected_output.txt`) |
| `code_tests` | Submit; the tests must pass | `bootdev.py fetch <uuid>` | `check` prints PASS. It runs the submit cases too, so a local PASS is the same bar as Boot.dev's Submit |
| `choice` | Click an answer | Ask the question in chat with its options, word for word | The user picks the answer-key option |
| `interview_chat` | An essay chat with Boots until Boot.dev's AI accepts the answer | Post `studentPrompt` in chat; you are the grader | The answer meets every point in `acceptanceCriteria`, or, when that is empty, the readme's main claims. When it falls short, ask one narrower question at the gap and let them revise; keep going until it passes |
| `text_input` | Paste a command's output | The user runs the readme's command in their own terminal and pastes the output in chat | The output is what the readme's command produces |
| `cli` | `bootdev run <uuid>` to test, `bootdev run <uuid> -s` to submit, in the user's own project | This is already local; the user runs the CLI | The submit run passes |
| `shell` | Boot.dev's in-browser terminal | The user runs the commands in their own shell and pastes the last command | The pasted command satisfies `shellData.checks` |
| `github_checks` | Boot.dev checks the user's GitHub repo | None: GitHub is the environment | Boot.dev only |

The answer key and any solution stay out of chat until the lesson has ended.

When `check` reports that a runner is missing (`node`, `python3`/`pytest`, `npx`, `go`), offer to install it, or have the user finish that lesson on Boot.dev.
