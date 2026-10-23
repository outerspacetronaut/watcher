# Getting started with GPT/Codex

Start with a small nonproduction project on a dedicated Linux runner. Read
[threat-model.md](threat-model.md) before giving the bot access. The GPT adapter has
offline tests and passing GitHub CI; a complete authenticated card-to-merged-PR pilot
and GPT live replay parity remain unvalidated. This guide prepares that pilot, not a
claim that unattended GPT operation is ready.

## 1. Check out the GPT revision

The fork is [outerspacetronaut/watcher](https://github.com/outerspacetronaut/watcher).
The initial integration is on `feat/codex-backend`, in
[draft PR #1](https://github.com/outerspacetronaut/watcher/pull/1). Until it merges,
check out that branch explicitly:

```bash
git clone https://github.com/outerspacetronaut/watcher.git
cd watcher
git switch feat/codex-backend
python3 bin/test-codex-runner.py
```

**Check:** `bin/codex-runner.py` exists and the adapter tests pass. A checkout of the
original upstream or an older `main` does not contain the GPT adapter.

## 2. Scope the GitHub identity and project files

Use a dedicated bot GitHub account with write access only to the pilot repository
and its Projects board. Keep repo administration on your own account.

The tracked `projects/*.env` and `projects/*.detect.env` files describe Steve's
upstream installation. Remove or replace those live configs in your deployment
checkout before running the installer. Keep the `.env.txt` examples as references.
The installer enables detector timers for every live detector config it finds;
copying the upstream configs does not provision your own board.

**Check:** every live config names a repository, board, and path you control. See
[projects/README.md](../projects/README.md).

## 3. Prepare the runner and sign in

Use a persistent Debian 12 VM or LXC with systemd (4 cores and 8 GB is the original
setup), with no production credentials or unrelated personal files. As root, clone
your prepared revision into `/opt/watcher`, then run:

```bash
/opt/watcher/deploy/bootstrap.sh
npm install -g @openai/codex
/opt/watcher/deploy/install.sh
```

Bootstrap still installs Claude Code as part of the original setup; Codex is the
additional install above. The installer creates the `watcher` user, units,
`/etc/watcher/env`, the floor service, and deployment/metrics timers. For the pilot,
stop automatic deployment until the live validation path is ready:

```bash
systemctl stop watcher-deploy.timer
su - watcher
gh auth login
gh auth setup-git
codex login --device-auth
codex login status
```

Complete ChatGPT sign-in with your own eligible account. The GitHub connection and
login in this chat do not authenticate a separate runner. Codex manages the saved
login; do not paste credentials into git or `/etc/watcher/env`. Optional Discord or
Slack webhook URLs belong in `/etc/watcher/env`.

**Check:** `gh auth status` names the bot and `codex login status` reports ChatGPT
sign-in **as watcher**. The installer's missing `CLAUDE_CODE_OAUTH_TOKEN` reminder is
legacy and does not apply to a Codex-only lane. Do not add a Claude token to clear it.
Leave project lanes stopped while completing the next steps.

## 4. Configure the first project for GPT

On your own machine, authenticated as yourself, use the existing setup script:

```bash
BOT_LOGIN=<bot-login> deploy/add-project.sh <name> <owner/repo>
```

The script creates a board and its required fields, links the repo, creates labels,
and configures the named CI check and PR requirement. Optionally set
`TEMPLATE_BOARD=<owner>/<number>` to copy an existing accessible board instead. It asks you to grant bot board access and enable Auto-add with
`is:issue is:open`; copied boards do not carry that workflow across.

The generated project file uses the legacy launcher defaults. **Before installing
or starting the lane**, append these GPT settings to `projects/<name>.env`:

```bash
WATCHER_CLAUDE="${WATCHER_HOME:-/opt/watcher}/bin/codex-runner.py"
TICK_MAX_TURNS=0
TICK_MAX_BUDGET_USD=0
TICK_TIMEOUT=30
export WATCHER_CODEX_SANDBOX=workspace-write
```

For manual configuration, [example-codex.env.txt](../projects/example-codex.env.txt)
is a complete starter; fill in your real board and repo instead of appending the
whole starter to an existing config. Use the correct absolute fallback if your
install is not `/opt/watcher`. Every child lane must inherit these GPT settings.

The adapter uses ChatGPT sign-in. It rejects nonzero Claude turn/dollar limits;
the finite watchdog is the tick's time bound. `workspace-write` is the restricted
default and can block git/network steps. Broader `danger-full-access` is an explicit
choice for a dedicated runner. See [codex.md](codex.md) before changing it.

## 5. Prepare project instructions and checks

Before its first tick, fill in [templates/project-CLAUDE.md](../templates/project-CLAUDE.md)
in the project's `CLAUDE.md`. Keep the exact phrase
``required CI check is `<name>` ``: `bin/doctor.sh` reads it. Give Codex an `AGENTS.md`
that points to that file, and create `docs/board.md` from
[templates/board.md](../templates/board.md) using the actual board values printed by
`add-project.sh`.

Configure the project's review-receipt job and require it alongside its build check;
`add-project.sh` does not install that second gate for you. Separate reviewer runs
and exact-commit receipts remain mandatory. Project command overrides and custom
agents must be checked for Claude-specific assumptions; they are not automatically
converted by selecting GPT.

Commit and push your project config and instructions. On the runner, as root:

```bash
/opt/watcher/deploy/install.sh <name>
su - watcher -c 'WATCHER_PROJECT=/opt/watcher/projects/<name>.env /opt/watcher/bin/spawn.sh --dry-run'
```

**Check:** doctor reports the correct board/checks, and dry-run's retained
`claude command` label names `codex-runner.py` with both limits set to zero. Populate
the project's required private inputs without committing secrets. Resolve warnings
about the board or CI; the legacy Claude-token reminder is the exception above.

## 6. Validate one card before unattended work

Choose a small, reversible pilot issue. With a single lane's default routing it can
be unlabeled; when splitting lanes, configure a triage lane or give it the correct
`agent:` label. Move it to **In progress**; `READY_PULL` stays off for this trial.
Start just the configured pilot lane:

```bash
systemctl start watcher@<name>
journalctl -u watcher@<name> -f
```

Watch `http://<runner-LAN-address>:8787/`. Verify the actual model completion,
normalized result and token usage, separate reviews, current-SHA receipts, required
checks, and resulting board state. Stop the lane after the trial. A timeout or failed
model login is a failed pilot, even if offline checks passed.

The existing live replay harness is Claude-specific and has not been ported to GPT.
Do not bypass it with `DEPLOY_EVALS=0` or `deploy-anyway` to declare this integration
ready. Complete the pilot and GPT replay work before enabling unattended lanes and
automatic deployment. No runner was deployed as part of the fork/PR work.

## 7. Answer a Stuck card

Read the newest comment's first line and lettered options. Reply on the card and
move it back to **In progress** when ready to retry. A retry resets a parked card's
attempt count. See [owner-cheat-sheet.md](owner-cheat-sheet.md) for daily operation
and [how-it-works.md](how-it-works.md) for the loop's mechanics.
