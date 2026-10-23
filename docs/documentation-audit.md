# GPT documentation review

Reviewed on October 23, 2026 for the GPT/Codex adapter branch. The setup is GPT-first;
the runtime still needs an explicit per-project launcher override. The original
Claude path remains supported, and compatibility filenames have not been renamed.

| Documentation | Review result |
|---|---|
| `README.md` | GPT entry point, setup links, actual CI jobs, deployment limits, upstream examples |
| `AGENTS.md`, `CLAUDE.md` | Native Codex entry point to shared rules; retained review/replay gates |
| `docs/getting-started.md` | GPT revision, runner sign-in, configuration before start, pilot order |
| `docs/codex.md` | Launcher, sandbox, reviews, logs, token accounting, known live gaps |
| `docs/how-it-works.md` | Provider map, lanes/canary behavior, normalized results, legacy-only limits |
| `docs/owner-cheat-sheet.md` | Conditional Ready queue, configured lanes, GPT usage/logs, deployment status |
| `docs/talking-to-the-owner.md` | GPT report line; numeric legacy equivalent only when actually returned |
| `docs/threat-model.md` | Saved ChatGPT login, shared host reach, sandbox, actual receipt guarantees |
| `docs/board.md` | Fork repo commands; no invented board, Auto-add state, or upstream writes |
| `commands/watch.md`, `commands/triage.md` | GPT tool execution/accounting and separate review calls; same workflow gates |
| `agents/reviewer.md`, `agents/usability.md` | Claude YAML compatibility, GPT model selection and separate read-only helpers |
| `templates/project-CLAUDE.md`, `templates/board.md` | GPT instructions and provider-independent board setup |
| `projects/README.md`, `projects/example-codex.env.txt` | Complete GPT starter and removal/replacement of upstream live configs |
| `projects/example.env.txt`, `projects/example-triage.env.txt` | Legacy defaults labeled; GPT child-lane inheritance explained |
| `projects/example.detect.env.txt` | Reviewed; detector is provider-independent, no model changes needed |
| `bin/hygiene-card.md` | Applicable replay gate retained; release-following behavior corrected |
| `.github/workflows/ci.yml`, `deploy/watcher@.service`, `bin/spawn.sh` comments | Fork runner, saved model login, receipt semantics; execution unchanged |
| `LICENSE.md` | Reviewed and retained: original MIT license and author attribution |

## Deliberately retained compatibility names

`WATCHER_CLAUDE`, `print_claude_cmd`, `CLAUDE.md`, `.claude/commands/`,
`.claude/agents/`, and transcript paths are still read by code or existing projects.
Agent YAML `model: opus` is legacy metadata stripped by the Codex adapter, not a GPT
model setting. `WATCHER_CODEX_MODEL` is the optional exported GPT model pin. Historical
links to Steve’s incidents and boards remain attributed upstream examples.

## Configuration correction

GPT examples use `WATCHER_CLAUDE="${WATCHER_HOME:-/opt/watcher}/bin/codex-runner.py"`.
The installer sources the project file before `WATCHER_HOME` exists; the fallback
avoids an unset-variable failure there. At tick launch, the exported `WATCHER_HOME`
selects the correct pinned release, including a canary checkout. Adapt the absolute
fallback when using a different install location.

## Evidence and remaining limits

The initial adapter passed offline tests and GitHub CI. CLI 0.164.0 accepted its
flags and reported ChatGPT sign-in; the live smoke attempt timed out without a
completed response. No successful GPT model/card run or unattended deployment is
claimed. The retained live replay harness uses Claude-specific limits and has not
been ported to GPT. Fixture tests do not establish live prompt compliance. Keep the
integration draft and retain all review, receipt, verification, and replay gates.

For the documentation revision, adapter tests (10), replay-fixture checks (56),
and project-setup checks (47) passed. The complete GPT example sourced successfully
under `bash -u` with `WATCHER_HOME` unset and with a canary release path supplied.
An attempted `WATCHER_CLAUDE="$PWD/bin/codex-runner.py" EVAL_JOBS=1 bash bin/eval.sh
happy-path` returned failure (`error_during_execution`), as expected from the
unsupported legacy limits; this is evidence of the remaining harness incompatibility,
not a passed behavioral replay.
