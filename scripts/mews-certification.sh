#!/usr/bin/env bash
# The mews nightly certification (FR-M4): every tripwire and the M1
# shakedown, once a day, with a report page that names per-pair verdicts
# and the sibling commits each verdict was measured against (FR-M6).
# Red pages notify; red never silently waits for someone to look.
#
# Install once per machine:
#   mkdir -p ~/.config/systemd/user
#   cp scripts/systemd/mews-certification.{service,timer} ~/.config/systemd/user/
#   systemctl --user daemon-reload && systemctl --user enable --now mews-certification.timer
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/mews"
mkdir -p "$STATE_DIR"
REPORT="$STATE_DIR/certification-last.md"
STAMP="$(date -u +%FT%TZ)"

cd "$REPO"
SIBLING_COMMITS=""
for bird in minder cupola windroos windtunnel; do
  dir="$HOME/projects/$bird"
  if [ -d "$dir/.git" ]; then
    commit="$(git -C "$dir" rev-parse --short main)"
    SIBLING_COMMITS="$SIBLING_COMMITS
- $bird: $commit"
  else
    SIBLING_COMMITS="$SIBLING_COMMITS
- $bird: absent (its tests skip with a reason)"
  fi
done

if OUT="$(env -u LD_LIBRARY_PATH python3 -m pytest tests/ -q 2>&1)"; then
  VERDICT="green"
else
  VERDICT="red"
fi

{
  echo "# mews nightly certification - $STAMP"
  echo
  echo "verdict: **$VERDICT**"
  echo
  echo "## Measured against (FR-M6 provenance)"
  echo "$SIBLING_COMMITS"
  echo
  echo "## Suite"
  echo '```'
  echo "$OUT" | tail -15
  echo '```'
  echo
  echo "A red verdict means a bird drifted or a seam broke: read the"
  echo "failing test's assertion, which names the pair and the missing"
  echo "piece. This page is the FR-M4 report; the console may render it"
  echo "later, the file is the authority."
} > "$REPORT"

# Model-drift probe (mews#8): the live engine's quality against the
# pinned baseline. Skips honestly when the engine is down (the night
# window owns it). A drift red turns the certification red.
DRIFT_LINE="$(python3 scripts/model_drift.py --report "$REPORT" --quiet 2>/dev/null)" \
  && DRIFT_RED=0 || DRIFT_RED=1
echo "$DRIFT_LINE"

if [ "$VERDICT" = "green" ] && [ "$DRIFT_RED" = "1" ]; then
  VERDICT="red"
fi

if [ "$VERDICT" = "red" ]; then
  notify-send -u critical "mews certification RED" \
    "report: $REPORT" 2>/dev/null || true
fi
echo "certification $VERDICT - report: $REPORT"
[ "$VERDICT" = "green" ]
