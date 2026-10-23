# Run Watcher with GPT through Codex

This fork adds an opt-in OpenAI Codex backend. Claude remains the default. The
adapter uses the existing `WATCHER_CLAUDE` launcher override; no board polling,
claim handling, retry, review receipt, or merge gate is replaced.

This is an initial integration with offline adapter coverage. A real authenticated
card-to-merged-PR run and the full live behavioral replay suite still need validation
on the operator's dedicated runner before unattended use.

## Set up the runner

Use the dedicated disposable Linux box in [getting-started.md](getting-started.md),
with git, Python 3, Node, GitHub CLI, Chromium, and the watcher user. The current
bootstrap also installs Claude Code; that is harmless, but Codex lanes do not need a
Claude login. The installer's missing-Claude-token reminder applies to Claude lanes.
Do not put a Claude token on a Codex-only box just to clear that reminder.

Install Codex from OpenAI's official npm package, then authenticate **as the watcher
user** using ChatGPT sign-in:

```bash
npm install -g @openai/codex
su - watcher
codex login --device-auth
codex login status
```

Complete the sign-in on the runner with your own eligible account. This chat's login
and GitHub connection are not automatically a login on that machine. Model access
and subscription usage limits follow the signed-in account.

This adapter deliberately requires ChatGPT authentication and removes inherited
`OPENAI_API_KEY` and `CODEX_API_KEY` from the child environment. It does not create,
copy, or store credentials. Codex manages its own authentication. API-key billing is
not supported by this adapter.

## Select Codex for a project

Create the project's ordinary board configuration as described upstream. Append
[example-codex.env.txt](../projects/example-codex.env.txt) to that project's env file,
then choose an appropriate sandbox for the dedicated runner:

```bash
WATCHER_CLAUDE="$WATCHER_HOME/bin/codex-runner.py"
TICK_MAX_TURNS=0
TICK_MAX_BUDGET_USD=0
TICK_TIMEOUT=30
export WATCHER_CODEX_SANDBOX=danger-full-access
```

`danger-full-access` grants the tick broad local access, as the original Claude loop
has on its disposable box. The adapter defaults to `workspace-write`; that mode can
edit files but may prevent git metadata writes or network operations needed for a
complete build/commit/push workflow. Use the default for a restricted trial; use broad
access only on the dedicated box with its scoped GitHub identity.

The legacy launcher's name still says `WATCHER_CLAUDE`, and `--dry-run` still prints
"claude command". Its executable should be `codex-runner.py`; a Claude installation
is not used for that lane. The example is `.env.txt`, so it cannot start a real lane.

Optional settings must be **exported** from a project file:

| Setting | Purpose |
|---|---|
| `WATCHER_CODEX` | Codex executable; default `codex` on PATH |
| `WATCHER_CODEX_MODEL` | Pin a model available to the signed-in account; otherwise use Codex's default |
| `WATCHER_CODEX_SANDBOX` | `workspace-write` by default; also `read-only` or `danger-full-access` |

Canary lanes use the same release-pinned adapter through `WATCHER_HOME`. Commands
come from `.claude/commands/<name>.md` in the project first, then the release's
`commands/`. Keeping those paths lets the existing projects work with both providers.
The adapter explicitly tells Codex to read project `AGENTS.md` and `CLAUDE.md`.

## Reviews and logs

The builder's prompt requires separate model runs for the existing reviewer and
usability passes. It supplies this helper rather than asking the builder to review
its own output:

```bash
python3 "$WATCHER_HOME/bin/codex-runner.py" --agent reviewer \
  --context-file "$scratch/review-context.txt"

python3 "$WATCHER_HOME/bin/codex-runner.py" --agent usability \
  --context-file "$scratch/usability-context.txt" --image "$scratch/phone.png"
```

Both use a read-only sandbox and ignore user configuration. Usability runs from an
empty directory with shell tools disabled; its context must contain only the ask,
You get line, exact commit, and supplied screenshots. These are process/sandbox and
prompt controls, not a new security boundary for arbitrary MCP tools or custom
project agent definitions. Project-specific agents may require further adaptation.
The existing review receipt check still decides whether a PR has the required
receipt for its exact commit. An unavailable required review must stop the merge.

The adapter writes a final JSON object with the fields the spawner already reads:
`subtype`, `is_error`, `result`, duration, turns, and token usage. `total_cost_usd` is
null: Codex token counts do not establish subscription-equivalent dollar cost.
`num_turns` counts Codex completed turns, not Claude assistant turns. Input cache
tokens are separated to prevent the existing metrics reader counting them twice.

Raw Codex events and normalized progress entries stream to a private JSONL file
under the existing transcript tree (`~/.claude/projects/`, or the canary config's
`projects/`). That path is compatibility storage; it does not mean Claude ran.
`tail.py`, the floor's Peek, and failed-tick transcript preservation can read it
without changes. A missing completion, nonzero exit, malformed event stream, or
failed turn is reported as failure, not a successful tick.
Child reviews write into a `reviews/` subdirectory, so a review cannot replace the
builder's transcript in Peek or failed-tick preservation.

## Limits and validation

Claude's `--max-turns` and `--max-budget-usd` have no equivalent in this adapter.
Nonzero values fail before Codex starts. Zero disables those two controls explicitly;
keep `TICK_TIMEOUT` finite. The spawner's process-group watchdog still bounds a tick
and its child review processes. Direct helper runs have no standalone watchdog.

Run the offline contract tests without credentials or network:

```bash
python3 bin/test-codex-runner.py
```

They cover command overrides, subscription-only invocation, success/failure event
handling, existing transcript readers, token accounting, reviewer separation,
usability inputs, and signal cleanup. They do not prove a model follows the workflow.

The upstream live replay harness uses Claude-specific per-case limits. It has not
been ported here; do not disable replay checks or claim it passed on Codex. Keep the
upstream Claude replay gate on an existing mixed-provider installation. On a new
Codex-only runner, manually validate a small nonproduction project before enabling
unattended work; full replay parity is follow-up work.

Official references:

- [Non-interactive Codex](https://learn.chatgpt.com/docs/non-interactive-mode)
- [Authentication](https://learn.chatgpt.com/docs/auth)
- [CLI reference](https://learn.chatgpt.com/docs/cli/reference)
- [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
