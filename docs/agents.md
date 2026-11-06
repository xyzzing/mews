# Running agents against the stack

Front-door content (FR-M5-adjacent): the environment and resource laws an
agent (or a human driving one) keeps tripping on, each with its why. Every
law here was learned by hitting the failure, not by prediction.

## Environment laws

- `env -u LD_LIBRARY_PATH` before any python in these repos. The ZCode
  appimage exports a library path that poisons subprocess python: imports
  resolve but C extensions crash, and the failure reads as a code bug.
  minder's Makefile and hooks encode this; the other repos just fail.
- `PYTHONPATH=src` for cupola's suite (layout is `src/cupola/`), and
  cupola's `tests/conftest.py` makes bare `pytest tests/` work too. minder
  and windroos run from the repo root with no path tricks.
- Sibling lookouts are env-overridable: `MEWS_SIBLINGS` (default
  `~/projects`) for the mews tripwires, `MINDER_WINDTUNNEL_REPO` for
  minder's mirror check. Point them elsewhere in CI or a container.
- `python3 -I` (isolated) in any subprocess that must not inherit a
  tampered path - but remember `-I` also drops `PYTHONPATH`, so pass
  explicit `sys.path.insert` lines instead.

## Resource laws

- The engine is a single slot. cupola serves one llama-server
  (`strata-8081.service`, loopback :8081, `total_slots: 1`); concurrent
  requests queue and the minder proxy answers with an honest 503 while it
  waits. Serialize engine-bound work; the proxy's retry handles the rest.
- Ports, all loopback: 8390 minder proxy (the supervised entry - point
  agents here, never at :8081 directly, or the ledger misses the request),
  8391 reflex sidecar, 8392 sink, 8765 operator console, 8081 engine.
- The engine belongs to whoever's window is open. A night-gates run
  (strata-amd) legitimately stops `strata-8081` for its whole window;
  check `systemctl --user is-active strata-8081` before blaming the proxy,
  and never restart the engine under another window's run.
- Minder's user units: proxy, sink, reflex, web console, plus three
  timers - `minder-doctor` (daily), `minder-capture-canary` (every 30 min,
  critical notify on red), `minder-capture-digest` (daily 09:00).

## Working near concurrent agents

- Other agents hold real checkouts with uncommitted work (minder's
  `minder_memory/lessons.py` has carried someone's edits for days). Never
  switch branches in a shared checkout - build PR branches in
  `git worktree add /tmp/...` off `origin/main`, and stage only your own
  files.
- A `/tmp` worktree changes two test outcomes in minder for environmental
  reasons only (the room-boundaries test resolves its windtunnel sibling
  via `../windtunnel`; the docs-gate test skips where `docs/` has no
  local-private files). Read the skip reasons with `pytest -rs` before
  attributing a delta to your change.
- Expect transient 503s and connection drops from the engine while it is
  being optimized or restarted mid-window; the workflow runtime retries
  those itself, and a stopped unit is not a bug.

## The verification vocabulary

- Green means the command ran and passed - never that nothing regressed.
  A skip is a reason, a missing sibling measures nothing, and a test that
  has never failed demonstrates nothing (proven-red is a CI job in minder,
  a discipline everywhere else).
- Every claim of engine work should be able to show a `token_usage` row in
  `~/.local/state/minder/events.jsonl` - that is what "went through the
  supervised path" means here.
