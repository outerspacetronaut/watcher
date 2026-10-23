# Threat model for the GPT/Codex runner

Watcher is an autonomous coding loop with GitHub write access. Its controls reduce
mistakes; they do not make an unattended model a trusted security principal. Use a
dedicated, disposable runner and scope every credential to what it actually needs.
A complete GPT pilot and live replay parity are still pending in this fork.

## What the runner holds

- A bot GitHub login, saved by `gh` **as watcher**. Its permissions are whatever you
  granted the account/token: repository writes, issue/PR actions, and board access.
  Keep administration on your own account; do not copy your personal token here.
- A saved Codex ChatGPT login, managed by Codex in its native credential storage
  (for example its auth file or configured credential store). Authenticate as the
  same watcher user that runs the lanes. The adapter does not create or copy it.
- Checkouts, card worktrees, state, result logs, and transcripts. The retained
  `.claude/projects/` tree holds compatibility transcripts, not the Codex login.
  Logs can contain private project data and command output; treat them accordingly.
- Optional Discord/Slack webhook URLs in `/etc/watcher/env`, and any private inputs
  deliberately supplied to a project. Do not commit credentials or webhook URLs.

Keep production secrets, personal files, cloud administration credentials, and keys
to other hosts off this box. Rebuilding it restores local state, not remote actions
already taken with a compromised credential. Revoke affected credentials separately.

## Sandbox and unattended execution

GPT lanes invoke `codex exec` with `approval_policy="never"`; no mid-run permission
prompt can be answered. The adapter’s default sandbox is `workspace-write`.
`WATCHER_CODEX_SANDBOX` can explicitly select `read-only` or `danger-full-access`.
The accepted `--dangerously-skip-permissions` flag is legacy compatibility and does
not choose the Codex sandbox.

A restricted trial can expose blocked git or network operations needed for a full
workflow. `danger-full-access` permits broad local access on the runner. Use it only
with an appropriate dedicated host and scoped identity. The host’s OS permissions,
network policy, available tools, native configuration, and credentials determine
what a tick can actually reach. A model instruction is not an OS restriction.

Lanes normally share the watcher OS identity and filesystem. A worktree, project
file, or canary checkout is not isolation from another lane’s checkout or secrets.
`CLAUDE_CONFIG_DIR` redirects compatibility state; it does not create an independent
Codex credential store or isolate native Codex settings.

## Authentication, usage, and time bounds

The adapter forces the OpenAI provider and ChatGPT login method and removes
`OPENAI_API_KEY` and `CODEX_API_KEY` from its child’s environment. API-key login is
not supported by this adapter. This is not removal of every possible project
credential or a guarantee about billing for other programs run by the tick.
ChatGPT account usage and access limits still apply.

GPT results report token usage and completed turns; `total_cost_usd` is **null**.
There is no GPT dollar-equivalent or turn ceiling here. The two Claude-specific
limits must explicitly be zero or the adapter refuses to start. Keep a finite
`TICK_TIMEOUT`: the spawner’s process-group watchdog bounds the tick and child
reviews. Direct helper invocations have no independent watchdog.

A project’s own API calls, deployment tools, or external services can incur charges
or change remote data if their credentials are available. The watcher’s ChatGPT
login and timeout are not caps on those actions. Inspect the project’s instructions
and credentials before allowing a pilot.

Legacy Claude lanes retain their original subscription-token/shim configuration
and usage-equivalent caps; see [how-it-works.md](how-it-works.md). A Codex-only lane
does not need `CLAUDE_CODE_OAUTH_TOKEN` merely to satisfy an installer reminder.

## What the bot can do

Within its actual permissions, a tick can read code, execute tools, edit files,
push branches, open/comment on PRs and issues, move cards, and request merges.
With broader sandbox access it may read other watcher-owned files and contact
reachable services. Misuse can expose data, consume allowance, change remote
resources, or leave unwanted branches/comments even if nothing merges.

The workflow forbids force-push, direct pushes to `main`, `--admin`, red merges,
secret access, and weakening gates. Branch protection can enforce some of these
independently **when configured and applicable to the bot**, but prose alone cannot.
Do not grant the bot an administrative bypass and call it protected.

## Merge and deployment gates

1. **Branch protection:** require PRs and the project’s actual build check on
   `main`. `deploy/add-project.sh` configures this first check; verify the resulting
   rules and the bot’s permissions on your repository.
2. **Verification:** the project’s tests and the card’s Verify block must pass.
   PR code can edit tests/workflows, so gate changes always get independent review.
   Run untrusted PR checks away from the operational runner’s credentials.
3. **Independent review and receipts:** the builder must obtain a separate
   `reviewer` verdict, plus `usability` first for a screen change. Codex helpers use
   read-only sandboxes and ignore user config; usability also disables shell tools
   and runs in an empty directory with supplied screenshots. These controls are
   not a blanket security boundary for arbitrary connectors or custom agent tools.
   An unavailable required review stops merging.
4. **Receipt check:** configure `review-receipt` as another required check. The
   builder posts the reviewer’s returned verdict naming the current full head SHA.
   `bin/receipt-check.sh` checks the required text and commit freshness. It rejects
   stale or missing receipts; it does **not** cryptographically authenticate a
   separate agent or prevent a malicious builder from fabricating matching text.
   A genuine independent review remains a required workflow action. Adding this
   gate to another project is a separate setup step; `add-project.sh` does not do it.
5. **Deployment:** the existing deployer checks `verify` and the live replay suite
   before release. The live harness is still Claude-specific; the GPT draft has
   not completed replay parity. Keep unattended deployment off during the pilot.
   Do not disable replay or use `deploy-anyway` to substitute for GPT validation.

These gates catch errors and stale evidence under the workflow’s trust assumptions.
They are not three unforgeable, independent security principals. Review gate changes
closely, keep operational credentials out of CI, and verify protection on the real
repo before enabling unattended work.

## Further reading

- [GPT adapter contract and limits](codex.md)
- [Pilot setup](getting-started.md)
- [Architecture and hard rules](how-it-works.md)
- [Tick workflow](../commands/watch.md)
- [Receipt implementation](../bin/receipt-check.sh)
- [Project setup implementation](../deploy/add-project.sh)
