# AGENTS.project.md - the mews

Architecture contracts: the mews owns no shape any bird owns; it consumes
published exchange schemas only (windtunnel.*/vN, minder event kinds,
windroos telemetry contracts, cupola contracts.py shapes). It contains no
runtime code and is imported by no bird.

Verification commands (M0 scope, grows with phases):

    python3 -m pytest -q        # tripwires (once they exist)
    ruff check .

Playbook table:

| Work | Read first |
|---|---|
| Tripwires, shakedown | docs/PRD.md SS3, SS4 |
| Front door content | docs/PRD.md SS3 FR-M5 |
