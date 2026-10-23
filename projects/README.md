# projects/

A **project file** (`projects/<name>.env`) tells one `bin/spawn.sh` instance which board
to watch and which repo its cards live in; a **lane file** (`projects/<name>-<lane>.env`)
sources a project file and overrides just enough (`PROJECT_NAME`, `LANE_AGENTS`, and
sometimes `LANE_COMMAND`/`LANE_WORKDIR`) to run a second instance beside the first that
takes a different slice of the same board — see `docs/how-it-works.md`, "Lanes". A
`.detect.env` file (sourced after its project file) opts that project into `bin/detect.sh`,
the product detector; merging one is what turns it on. `example.env.txt`,
`example-triage.env.txt` and `example.detect.env.txt` spell out the legacy runtime knobs each kind
takes, built from `bin/spawn.sh`'s and `bin/detect.sh`'s own header comments (a
`test-spawn.sh` case keeps the project-file one from drifting out of sync with the real
header). They are named `.env.txt`, not `.env`, on purpose: the installer's and the
spawner's own file discovery both glob `*.env` (and `*.detect.env`), so a `.txt` suffix is
what keeps these examples read as documentation and never as a project to start a timer or a
lane for. Copy one, drop the `.txt`, and fill in its blanks.

For GPT, start from **`example-codex.env.txt`**, a complete project config, or add
the GPT overlay from `docs/codex.md` to the short config written by `add-project.sh`.
The generated file and `example.env.txt` alone still select the legacy Claude
default. Export `WATCHER_CODEX*` settings; set both legacy CLI limits to zero and a
finite timeout. Child lanes source the real GPT project file so they inherit these.

Every live `.env`/`.detect.env` file in this directory — `riffmap*`, `riffmap-site*`, `azeroth-rewind*`,
`watcher.env` — is Steve's own: his boards, his bot, his repos. A fork of this repo
deletes every one of them and adds its own with `deploy/add-project.sh` (the normal path
for a single-lane project — it writes the short form directly) or the examples here (for
a second lane, the canary channel, or just to see what a knob does before setting it).
`watcher.env` gets one extra word: it is the watcher working **its own** board, the same
way this repo works any other project's, and a fork either re-points it at its own
watcher-board or deletes it along with the rest — see `CLAUDE.md`, "When the watcher works
its own board".
